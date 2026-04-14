"""
AI Agent tab - AI-powered video editing assistant.
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QGroupBox, QComboBox, QListWidget
)
from PySide6.QtCore import Qt

from ui.widgets.animated_button import AnimatedButton


class AIAgentTab(QWidget):
    """AI Agent tab for intelligent editing suggestions."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        title = QLabel("AI Agent")
        title.setObjectName("titleLabel")
        layout.addWidget(title)

        desc = QLabel("AI-powered assistant for video editing tasks")
        desc.setObjectName("subtitleLabel")
        layout.addWidget(desc)

        # Model selection
        model_group = QGroupBox("AI Model")
        model_layout = QVBoxLayout(model_group)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model:"))
        self.cmb_model = QComboBox()
        self.cmb_model.addItems(["GPT-4o", "GPT-3.5 Turbo", "Gemini Pro", "Claude 3"])
        model_row.addWidget(self.cmb_model)
        model_layout.addLayout(model_row)

        layout.addWidget(model_group)

        # Chat interface
        chat_group = QGroupBox("Chat with AI")
        chat_layout = QVBoxLayout(chat_group)

        self.txt_chat = QTextEdit()
        self.txt_chat.setReadOnly(True)
        self.txt_chat.setPlaceholderText("AI responses will appear here...")
        self.txt_chat.setMinimumHeight(200)
        chat_layout.addWidget(self.txt_chat)

        input_layout = QHBoxLayout()
        self.txt_input = QTextEdit()
        self.txt_input.setPlaceholderText("Ask AI to help with editing...")
        self.txt_input.setMaximumHeight(80)
        input_layout.addWidget(self.txt_input)

        self.btn_send = AnimatedButton("Send", color="#4A90D9")
        self.btn_send.setFixedWidth(80)
        self.btn_send.clicked.connect(self._send_message)
        input_layout.addWidget(self.btn_send)

        chat_layout.addLayout(input_layout)
        layout.addWidget(chat_group)

        # Quick actions
        actions_group = QGroupBox("Quick Actions")
        actions_layout = QVBoxLayout(actions_group)

        quick_actions = [
            ("Auto-generate subtitles", "Generate subtitles from video audio"),
            ("Suggest cuts", "AI analyzes video for best cut points"),
            ("Improve audio quality", "AI-powered audio enhancement"),
            ("Generate thumbnail", "Create a thumbnail from video"),
        ]

        for action_name, tooltip in quick_actions:
            btn = QPushButton(action_name)
            btn.setToolTip(tooltip)
            btn.clicked.connect(lambda checked, name=action_name: self._quick_action(name))
            actions_layout.addWidget(btn)

        layout.addWidget(actions_group)
        layout.addStretch()

    def _send_message(self):
        text = self.txt_input.toPlainText().strip()
        if not text:
            return

        self.txt_chat.append(f"\n[You]: {text}")
        self.txt_input.clear()

        # Mock AI response
        response = f"[AI Agent]: I understand you want to '{text}'. This feature will use the selected AI model to process your request. (Mock response - connect API key for real AI)"
        self.txt_chat.append(response)

    def _quick_action(self, action_name: str):
        self.txt_chat.append(f"\n[System]: Executing quick action: {action_name}...")
        self.txt_chat.append(f"[AI Agent]: Starting '{action_name}'... (Mock - requires API connection)")
