# Executive Meeting Prep Agent

**Built by Team CodeCrafters (Hyderabad, Sept 2026)**

An enterprise-grade, AI-powered RAG (Retrieval-Augmented Generation) agent that prepares executives for meetings by recalling past interactions, commitments, budget constraints, and communication preferences. 

Unlike standard chatbots, this agent utilizes a custom **Smart Vector Routing** logic to prevent vector pollution and strictly enforces a professional 4-section briefing format.

## Core Features

*   **Smart Vector Routing:** Pre-extracts emails and names from user queries to fetch exact entity data, completely bypassing standard vector semantic confusion.
*   **100% Anti-Hallucination:** Strictly bounded by the custom `Hindsight` database. If data (like a budget or promise) isn't in the vault, the AI explicitly states it cannot find it rather than guessing.
*   **Strict 4-Section Briefings:** Automatically formats prep queries into actionable insights:
    1. Contact Preferences & Communication Style
    2. What Was Promised & Commitments Made
    3. Missed Follow-ups, Objections & Budget Landmines
    4. Strategic Gameplan & Tactical Advice
*   **User Preference Learning:** Learns the executive's personal meeting style (e.g., "ultra-short bullet points", "aggressive closing") from the database and adapts its output tone dynamically.
*   **Emergency Failsafe:** Includes fallback logic to ensure the agent always returns context even if exact email prefix matching fails during edge-case queries.

## Tech Stack

*   **Backend Framework:** FastAPI (Python)
*   **Frontned** React, Html, CSS
*   **LLM Engine:** Groq API (Dynamically selects the best available Llama-3 model)
*   **Vector/Memory Store:** Hindsight Helper (Custom context retention and retrieval module)
*   **CORS & Middleware:** Integrated for seamless frontend-backend communication.

## Getting Started

### Prerequisites
* Python 3.9+
* A valid Groq API Key

### Installation

1. **Clone the repository**
   ```bash
   git clone [https://github.com/muskanlalwani155-design/codecrafters-meeting-prep-agent.git](https://github.com/muskanlalwani155-design/codecrafters-meeting-prep-agent.git)
   cd codecrafters-meeting-prep-agent
