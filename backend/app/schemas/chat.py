from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class ChatMessage(BaseModel):
    role: str  # user | assistant
    content: str


class ChatRequest(BaseModel):
    question: str
    conversation_history: Optional[List[ChatMessage]] = []


class ChartData(BaseModel):
    chart_type: str  # line | bar | pie
    title: str
    data: List[Dict[str, Any]]
    x_key: Optional[str] = None
    y_key: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    chart: Optional[ChartData] = None
    supporting_reviews: Optional[List[Dict[str, Any]]] = []
    confidence: Optional[float] = None
