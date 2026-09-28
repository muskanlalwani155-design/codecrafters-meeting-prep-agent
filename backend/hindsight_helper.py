import os
import re
from dotenv import load_dotenv
from hindsight_client import Hindsight

load_dotenv()

HINDSIGHT_BASE_URL = os.getenv("HINDSIGHT_BASE_URL", "https://api.hindsight.vectorize.io")
HINDSIGHT_API_KEY = os.getenv("HINDSIGHT_API_KEY")
BANK_ID = os.getenv("HINDSIGHT_BANK_ID", "meeting_prep_bank")

client = Hindsight(
    base_url=HINDSIGHT_BASE_URL,
    api_key=HINDSIGHT_API_KEY
)

def extract_emails(text):
    if not text: return []
    raw_emails = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+', text)
    return list(set([e.lower() for e in raw_emails]))

def retain_meeting_notes(contact_name: str, email: str, notes: str, meeting_date: str):
    clean_email = email.lower().strip()
    domain = clean_email.split('@')[1].split('.')[0].capitalize() if '@' in clean_email else ""
    content = f"The official email ID for {contact_name} is {clean_email}. They work at {domain}. Meeting Date: {meeting_date}. Notes: {notes}"
    print(f"\n[RETAINING]: {content}")
    try:
        res = client.retain(
            bank_id=BANK_ID,
            content=content,
            context="executive_meeting_briefing"
        )
        return {"status": "success", "result": str(res)}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

def recall_contact_history(query: str):
    print(f"\n[RECALLING QUERY]: {query}")
    try:
        result = client.recall(
            bank_id=BANK_ID,
            query=query
        )
        
        query_lower = query.lower()
        raw_items = []
        if hasattr(result, "results") and result.results:
            raw_items = [getattr(item, "text", None) or getattr(item, "content", None) or str(item) for item in result.results]
        elif isinstance(result, list):
            raw_items = [str(item) for item in result]

        found_emails = set()
        for item in raw_items:
            for e in extract_emails(item):
                found_emails.add(e)

        print(f"[FOUND EMAILS IN DB]: {found_emails}")

        query_emails = extract_emails(query_lower)
        user_email = query_emails[0] if query_emails else None

        if not user_email and len(found_emails) > 1:
            emails_list = "\n".join([f"- {e}" for e in found_emails])
            ambiguity_msg = f"Mujhe is naam ki multiple profiles mili hain. Kripya apni required Email ID choose karein:\n{emails_list}"
            return [{"text": ambiguity_msg}]

        extracted_facts = []
        for item in raw_items:
            if not item: continue
            is_match = True
            
            if user_email:
                item_emails = extract_emails(item)
                if item_emails and user_email not in item_emails:
                    is_match = False

            if is_match:
                extracted_facts.append({"text": item})

        if not extracted_facts and raw_items:
            extracted_facts = [{"text": i} for i in raw_items if i]

        return extracted_facts
    except Exception as e:
        print(f"[RECALL ERROR]: {e}")
        return []