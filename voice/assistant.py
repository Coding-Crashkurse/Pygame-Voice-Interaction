from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Literal, Sequence, TypedDict

from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field

IntentLabel = Literal["trade", "smalltalk", "unknown"]


class IntentPrediction(BaseModel):
    intent: IntentLabel = Field(description="Predicted conversation intent")
    item: str | None = Field(
        default=None,
        description="Name of the item the visitor wants to trade for, if any",
    )
    confidence: float | None = Field(
        default=None,
        description="Confidence score between 0 and 1 if the model can provide one",
    )
    rationale: str | None = Field(
        default=None, description="Short reasoning for the decision"
    )


@dataclass
class PurchaseOutcome:
    success: bool
    item_name: str | None
    message: str
    price_paid: int | None = None


class MerchantState(TypedDict, total=False):
    messages: list[BaseMessage]
    user_input: str
    intent: IntentLabel
    candidate_item: str | None
    response_text: str
    trade_result: PurchaseOutcome | None


@dataclass
class AssistantResult:
    intent: IntentLabel
    text: str
    candidate_item: str | None
    trade_result: PurchaseOutcome | None
    raw_state: MerchantState


class MerchantVoiceAssistant:
    """Conversation orchestrator using LangGraph with in-memory history."""

    def __init__(
        self,
        items: Sequence[dict],
        purchase_handler: Callable[[str | None], PurchaseOutcome],
        *,
        thread_namespace: str = "merchant",
        visitor_name: str | None = None,
    ) -> None:
        if not items:
            raise ValueError("MerchantVoiceAssistant requires at least one item")
        self._items = list(items)
        self._purchase_handler = purchase_handler
        self._thread_namespace = thread_namespace
        visitor = (visitor_name or "traveler").strip()
        self._visitor_name = visitor or "traveler"
        self._catalog_text = "\n".join(
            f"- {item['name']} ({item['type']}) costs {item['price']} gold. {item['bonus']}"
            for item in self._items
        )

        chat_model_name = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise EnvironmentError("OPENAI_API_KEY must be set for voice interactions")

        self._classifier = ChatOpenAI(
            model=chat_model_name,
            temperature=1.0,
            api_key=api_key,
        )
        self._responder = ChatOpenAI(
            model=chat_model_name,
            temperature=1.0,
            api_key=api_key,
        )

        self._intent_chain = self._build_intent_chain()
        self._smalltalk_chain = self._build_smalltalk_chain()
        self._trade_chain = self._build_trade_chain()
        self._fallback_chain = self._build_fallback_chain()

        self._checkpointer = MemorySaver()
        self._graph = self._build_graph()

    def _build_intent_chain(self) -> ChatPromptTemplate:
        system_message = f"""You are an intent classifier for a medieval merchant speaking with {self._visitor_name}. Given the conversation, decide if the visitor wants to trade for an item from the catalog below or simply engage in smalltalk. If you cannot tell, choose unknown.

Catalog:
{{catalog}}
"""
        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_message),
                MessagesPlaceholder("conversation"),
            ]
        )
        return prompt | self._classifier.with_structured_output(IntentPrediction)

    def _build_smalltalk_chain(self) -> ChatPromptTemplate:
        system_message = (
            f"You are Mira, a friendly village merchant. You are speaking with {self._visitor_name}. "
            "Engage in casual conversation while subtly keeping the mood light and warm. "
            "Keep responses concise enough for voice playback (<= 3 sentences)."
        )
        return (
            ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    MessagesPlaceholder("conversation"),
                ]
            )
            | self._responder
        )

    def _build_trade_chain(self) -> ChatPromptTemplate:
        system_message = f"""You are Mira, a helpful but honest merchant. You are speaking with {self._visitor_name}. Use the catalog below when confirming trades.
Catalog:
{{catalog}}
You received the summarized purchase result: {{purchase_message}}. If the trade succeeded, confirm the sale warmly and mention the price. If it failed, explain why and offer alternatives from the catalog. Keep responses <= 3 sentences for voice playback."""
        return (
            ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    MessagesPlaceholder("conversation"),
                ]
            )
            | self._responder
        )

    def _build_fallback_chain(self) -> ChatPromptTemplate:
        system_message = (
            f"You are Mira the merchant. You are speaking with {self._visitor_name}. "
            "Ask gentle clarifying questions when you are unsure about the visitor's request. "
            "Keep responses <= 2 sentences."
        )
        return (
            ChatPromptTemplate.from_messages(
                [
                    ("system", system_message),
                    MessagesPlaceholder("conversation"),
                ]
            )
            | self._responder
        )

    def _build_graph(self):
        workflow = StateGraph(MerchantState)
        workflow.add_node("add_user", self._add_user_message)
        workflow.add_node("classify", self._classify_intent)
        workflow.add_node("respond_trade", self._respond_trade)
        workflow.add_node("respond_smalltalk", self._respond_smalltalk)
        workflow.add_node("respond_unknown", self._respond_unknown)

        workflow.set_entry_point("add_user")
        workflow.add_edge("add_user", "classify")
        workflow.add_conditional_edges(
            "classify",
            self._route_intent,
            {
                "trade": "respond_trade",
                "smalltalk": "respond_smalltalk",
                "unknown": "respond_unknown",
            },
        )
        workflow.add_edge("respond_trade", END)
        workflow.add_edge("respond_smalltalk", END)
        workflow.add_edge("respond_unknown", END)

        return workflow.compile(checkpointer=self._checkpointer)

    # --- graph nodes -----------------------------------------------------

    def _add_user_message(self, state: MerchantState | None) -> MerchantState:
        if state is None:
            state = {}  # type: ignore[assignment]
        messages = list(state.get("messages") or [])
        user_input = str(state.get("user_input", "")).strip()
        if user_input:
            messages.append(HumanMessage(content=user_input))
        state["messages"] = messages
        return state

    def _classify_intent(self, state: MerchantState) -> MerchantState:
        prediction: IntentPrediction = self._intent_chain.invoke(
            {
                "conversation": state.get("messages", []),
                "catalog": self._catalog_text,
            }
        )
        data = (
            prediction.model_dump()
            if hasattr(prediction, "model_dump")
            else prediction.dict()
        )
        print("[MerchantAssistant] Intent prediction:", data)
        state["intent"] = prediction.intent
        state["candidate_item"] = prediction.item.strip() if prediction.item else None
        return state

    def _respond_smalltalk(self, state: MerchantState) -> MerchantState:
        response = self._smalltalk_chain.invoke(
            {"conversation": state.get("messages", [])}
        )
        print(f"[MerchantAssistant] Smalltalk response: {response!r}")
        state = self._append_response(state, response)
        return state

    def _respond_trade(self, state: MerchantState) -> MerchantState:
        candidate = state.get("candidate_item")
        print(f"[MerchantAssistant] Trade candidate: {candidate!r}")
        outcome = self._purchase_handler(candidate)
        print(
            "[MerchantAssistant] Trade outcome success={s} item={item} message={msg!r}".format(
                s=outcome.success,
                item=outcome.item_name,
                msg=outcome.message,
            )
        )
        state["trade_result"] = outcome
        response = self._trade_chain.invoke(
            {
                "conversation": state.get("messages", []),
                "catalog": self._catalog_text,
                "purchase_message": outcome.message,
                "visitor": self._visitor_name,
            }
        )
        state = self._append_response(state, response)
        print(
            "[MerchantAssistant] Trade response: {0!r}".format(
                state.get("response_text")
            )
        )
        return state

    def _respond_unknown(self, state: MerchantState) -> MerchantState:
        response = self._fallback_chain.invoke(
            {"conversation": state.get("messages", [])}
        )
        print(f"[MerchantAssistant] Unknown response: {response!r}")
        state = self._append_response(state, response)
        return state

    def _append_response(
        self, state: MerchantState, response: str | AIMessage
    ) -> MerchantState:
        messages = list(state.get("messages", []))
        if isinstance(response, str):
            ai_message = AIMessage(content=response)
        else:
            ai_message = response
        messages.append(ai_message)
        state["messages"] = messages
        state["response_text"] = ai_message.content
        return state

    def _route_intent(self, state: MerchantState) -> IntentLabel:
        intent = state.get("intent", "unknown")
        if intent not in ("trade", "smalltalk"):
            return "unknown"
        return intent

    # --- public API ------------------------------------------------------

    def reset_conversation(self, thread_id: str) -> None:
        """Clear stored chat history for a specific thread."""
        self._checkpointer.delete(self._thread_namespace, thread_id)

    def process(self, user_input: str, thread_id: str) -> AssistantResult:
        if not user_input.strip():
            raise ValueError("user_input must not be empty")
        print(
            f"[MerchantAssistant] process called with input: {user_input!r} thread_id={thread_id}"
        )
        state: MerchantState = self._graph.invoke(
            {"user_input": user_input},
            config={
                "configurable": {"thread_id": f"{self._thread_namespace}:{thread_id}"}
            },
        )
        print(
            "[MerchantAssistant] Graph state intent={intent} candidate={candidate} response={response!r}".format(
                intent=state.get("intent"),
                candidate=state.get("candidate_item"),
                response=state.get("response_text"),
            )
        )
        if state.get("trade_result"):
            trade = state["trade_result"]
            print(
                "[MerchantAssistant] Graph trade success={s} item={item} message={msg!r}".format(
                    s=trade.success,
                    item=trade.item_name,
                    msg=trade.message,
                )
            )
        return AssistantResult(
            intent=state.get("intent", "unknown"),
            text=state.get("response_text", ""),
            candidate_item=state.get("candidate_item"),
            trade_result=state.get("trade_result"),
            raw_state=state,
        )
