import os
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from hindsight_helper import retain_meeting_notes, recall_contact_history

load_dotenv()

app = FastAPI(title="Executive Meeting Prep Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

class ChatRequest(BaseModel):
    query: str

class MeetingNoteRequest(BaseModel):
    contact_name: str
    email: str
    meeting_date: str
    notes: str

@app.post("/api/retain")
def save_notes(req: MeetingNoteRequest):
    result = retain_meeting_notes(req.contact_name, req.email, req.notes, req.meeting_date)
    return {"message": "Context stored", "data": result}

@app.post("/api/chat")
def chat_endpoint(req: ChatRequest):
    query = req.query.strip().lower()
    
    def extract_emails(text: str):
        return set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text.lower()))

    query_emails = extract_emails(query)
    
    stop_words = {"prepare", "me", "for", "my", "call", "with", "meeting", "about", "discuss", "today"}
    query_words = [w for w in query.split() if w not in stop_words and len(w) > 2]
    clean_name = " ".join(query_words) if query_words else query

    # Helper function for AI generation
    def generate_briefing(identifier, context_str):
        system_prompt = f"""You are an expert Executive Meeting Prep Agent. Read the MEMORY VAULT below and organize the information into the 4 required sections.

        TARGET: {identifier}

        MEMORY VAULT:
        {context_str}

        INSTRUCTIONS:
        - Extract contact preferences, communication style, promises made (e.g. whitepapers, deadlines), objections, and budgets (e.g. 90 Lakhs).
        - Use standard hyphens (-) for bullet points. Do not use markdown bolding.
        - You must output all 4 headers below based on the vault notes.

        Format EXACTLY like this:
        CONTACT PREFERENCES & COMMUNICATION STYLE
        - [Point]

        WHAT WAS PROMISED & COMMITMENTS MADE
        - [Point]

        MISSED FOLLOW-UPS, OBJECTIONS & BUDGET LANDMINES
        - [Point]

        STRATEGIC GAMEPLAN & TACTICAL ADVICE FOR TODAY'S CALL
        - [Point]
        """
        try:
            available_models = groq_client.models.list().data
            valid_models = [m.id for m in available_models if "canopylabs" not in m.id.lower() and "guard" not in m.id.lower() and "vision" not in m.id.lower() and "whisper" not in m.id.lower()]
            
            ACTIVE_MODEL = valid_models[0] if valid_models else "llama-3.3-70b-versatile"
            for m_id in valid_models:
                if "70b" in m_id.lower() or "versatile" in m_id.lower():
                    ACTIVE_MODEL = m_id
                    break

            completion = groq_client.chat.completions.create(
                model=ACTIVE_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Generate the briefing for {identifier}."}
                ],
                temperature=0.1,
                max_tokens=600
            )
            reply = completion.choices[0].message.content
            if not reply or not reply.strip():
                return {"reply": f"CONTACT PREFERENCES & COMMUNICATION STYLE\n- Direct communication.\n\nWHAT WAS PROMISED & COMMITMENTS MADE\n- {context_str}\n\nMISSED FOLLOW-UPS, OBJECTIONS & BUDGET LANDMINES\n- Reviewed from memory.\n\nSTRATEGIC GAMEPLAN & TACTICAL ADVICE FOR TODAY'S CALL\n- Proceed with notes.", "memories": []}
            return {"reply": reply.strip(), "memories": []}
        except Exception as e:
            return {"reply": f"Briefing from Vault:\n\n{context_str}", "memories": []}

    try:
      
        if query_emails:
            target_email = list(query_emails)[0]
            base_name = target_email.split('@')[0].split('.')[0].lower()
            
            try:
                raw_memories = recall_contact_history(target_email)
                if not raw_memories:
                    raw_memories = recall_contact_history(base_name)
            except Exception:
                raw_memories = []

            valid_blocks = []
            for m in raw_memories:
                val = m.get("text", "") if isinstance(m, dict) else str(m)
                val_lower = val.lower()
                if target_email in val_lower or base_name in val_lower:
                    if val.strip() and val.strip() not in valid_blocks:
                        valid_blocks.append(val.strip())

            if not valid_blocks:
                return {"reply": f"No memory records found for {target_email}.", "memories": []}

            context_str = "\n\n".join(valid_blocks)
            return generate_briefing(target_email, context_str)

       
        else:
            try:
                raw_memories = recall_contact_history(clean_name)
            except Exception:
                raw_memories = []

            search_tokens = [t.lower() for t in clean_name.split() if len(t) > 1]
            verified_blocks = []
            found_emails = set()

            for m in raw_memories:
                val = m.get("text", "") if isinstance(m, dict) else str(m)
                val_lower = val.lower()
                
                matched = False
                if search_tokens:
                    if any(token in val_lower for token in search_tokens):
                        matched = True
                else:
                    if clean_name in val_lower:
                        matched = True

                if matched:
                    verified_blocks.append(val.strip())
                    found_emails.update(extract_emails(val_lower))

            if not verified_blocks:
                return {"reply": f"No records found for '{clean_name}' in the database.", "memories": []}

            matched_emails = set()
            for e in found_emails:
                local_part = e.split('@')[0].lower()
                if any(token in local_part for token in search_tokens):
                    matched_emails.add(e)

            if len(matched_emails) > 1:
                email_list = "\n".join([f"- {e}" for e in matched_emails])
                return {
                    "reply": f"I found multiple profiles matching '{clean_name}'. Please specify the exact email address:\n{email_list}",
                    "memories": []
                }
            elif len(matched_emails) == 1:
                target_email = list(matched_emails)[0]
                email_blocks = [b for b in verified_blocks if target_email in b.lower() or search_tokens[0] in b.lower()]
                context_str = "\n\n".join(email_blocks) if email_blocks else "\n\n".join(verified_blocks)
                return generate_briefing(target_email, context_str)
            else:
                context_str = "\n\n".join(verified_blocks)
                return generate_briefing(clean_name, context_str)

    except Exception as e:
        return {"reply": f"An error occurred: {str(e)}", "memories": []}