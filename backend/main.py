import os
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
from hindsight_helper import retain_meeting_notes, recall_contact_history, extract_emails

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
    query = req.query.strip()
    query_lower = query.lower()
    
    try:
        user_provided_emails = extract_emails(query_lower)
        
        prep_keywords = [
            "prepare me for my meeting with", "prepare me for my call with", 
            "prepare a call with", "prepare call with", "meeting with", 
            "call with", "prepare for", "brief me on", "notes for", "prepare"
        ]
        
        is_prep_query = False
        target_name = query_lower
        
        for k in prep_keywords:
            if k in target_name:
                is_prep_query = True
                target_name = target_name.replace(k, "").strip()
                target_name = target_name.replace("my", "").replace("today", "").strip()
                if target_name.startswith("a "): 
                    target_name = target_name[2:].strip()
                break
                
        # SMART VECTOR SEARCH
        if user_provided_emails:
            email_prefix = user_provided_emails[0].split('@')[0]
            search_term = email_prefix.replace('.', ' ').replace('_', ' ')
        elif is_prep_query and target_name:
            search_term = target_name
        else:
            search_term = query_lower
            
        raw_memories = recall_contact_history(search_term)

        found_emails = set()
        for m in raw_memories:
            found_emails.update(extract_emails(m))
            
        relevant_emails = set()
        matched_name = ""
        
        if is_prep_query and target_name:
            for e in found_emails:
                if target_name in e.lower() or search_term in e.lower():
                    relevant_emails.add(e)
            matched_name = target_name
        else:
            tokens = [t for t in query_lower.split() if len(t) > 2]
            for e in found_emails:
                local_name = e.split('@')[0].lower()
                for t in tokens:
                    if t in local_name:
                        relevant_emails.add(e)
                        matched_name = t
                        break

        if not user_provided_emails and len(relevant_emails) > 1:
            email_list = "\n".join([f"- {e}" for e in relevant_emails])
            return {
                "reply": f"I found multiple profiles matching '{matched_name.title()}'. Please specify the exact email address:\n{email_list}",
                "memories": []
            }
            
        # EMERGENCY FAILSAFE FILTERING
        filtered_memories = []
        if user_provided_emails:
            target_email = user_provided_emails[0]
            filtered_memories = [m for m in raw_memories if target_email in m.lower()]
            if not filtered_memories: 
                filtered_memories = raw_memories # Failsafe fallback
        elif len(relevant_emails) == 1:
            target_email = list(relevant_emails)[0]
            filtered_memories = [m for m in raw_memories if target_email in m.lower()]
            if not filtered_memories:
                filtered_memories = raw_memories # Failsafe fallback
        else:
            filtered_memories = raw_memories

        if not filtered_memories:
            return {"reply": f"No records found for your query.", "memories": []}

        context_str = "\n\n".join(filtered_memories[:5])

        system_prompt = f"""You are an expert Executive Meeting Prep Agent.
        Read the MEMORY VAULT below and answer the user's query.

        MEMORY VAULT:
        {context_str}

        INSTRUCTIONS:
        1. IF the user is asking to prepare for a call/meeting with a specific person, organize the information EXACTLY into these 4 sections. You MUST print all 4 headers. If no info is found for a section, write "No data found":
           CONTACT PREFERENCES & COMMUNICATION STYLE
           - [Point]
           WHAT WAS PROMISED & COMMITMENTS MADE
           - [Point]
           MISSED FOLLOW-UPS, OBJECTIONS & BUDGET LANDMINES
           - [Point]
           STRATEGIC GAMEPLAN & TACTICAL ADVICE FOR TODAY'S CALL
           - [Point]

        2. LEARN USER PREFERENCES: If the Memory Vault contains any notes about the USER'S OWN meeting style or preparation preferences, adapt your tone, formatting length, and strategic advice to strictly match their personal style.
           
        3. IF the user is asking a general question, DO NOT use the 4 sections. Answer conversationally and directly based ONLY on the Memory Vault. State the name clearly.
        
        4. If the answer is not in the Memory Vault, say "I couldn't find any information about that in the database." Do not hallucinate.
        """

        try:
            available_models = groq_client.models.list().data
            valid_models = [
                m.id for m in available_models 
                if "vision" not in m.id.lower() 
                and "whisper" not in m.id.lower()
                and "guard" not in m.id.lower()
                and "embed" not in m.id.lower()
                and "canopylabs" not in m.id.lower()
            ]
            
            if valid_models:
                ACTIVE_MODEL = valid_models[0]
                for m_id in valid_models:
                    if "llama3" in m_id.lower() or "llama-3" in m_id.lower():
                        ACTIVE_MODEL = m_id
                        break
            else:
                ACTIVE_MODEL = "mixtral-8x7b-32768" 
                
        except Exception:
            ACTIVE_MODEL = "mixtral-8x7b-32768" 

        completion = groq_client.chat.completions.create(
            model=ACTIVE_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"User Query: {query}"}
            ],
            temperature=0.1,
            max_tokens=1024
        )
        
        reply = completion.choices[0].message.content
        return {"reply": reply.strip(), "memories": []}

    except Exception as e:
        return {"reply": f"An error occurred: {str(e)}", "memories": []}