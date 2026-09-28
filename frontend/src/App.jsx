import React, { useState } from "react";
import axios from "axios";
import "./App.css";

const API_BASE = "http://127.0.0.1:8000/api";

function App() {
  const [contactName, setContactName] = useState("");
  const [contactEmail, setContactEmail] = useState(""); 
  const [meetingDate, setMeetingDate] = useState("");
  const [notes, setNotes] = useState("");
  const [retainStatus, setRetainStatus] = useState("");
  const [memories, setMemories] = useState(null);

  const [messages, setMessages] = useState([
    { sender: "ai", text: "Hello! I am your Meeting Prep Agent. Who are you meeting with today?" }
  ]);
  const [chatInput, setChatInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleReset = () => {
    setContactName("");
    setContactEmail(""); 
    setMeetingDate("");
    setNotes("");
    setRetainStatus("");
    setMemories(null);
    setMessages([{ sender: "ai", text: "Workspace reset! Who are you meeting with today?" }]);
  };

  const handleRetain = async () => {
    if (!notes.trim() || !contactName.trim() || !contactEmail.trim()) {
      setRetainStatus("⚠️ Please enter contact name, email, and notes.");
      return;
    }
    setRetainStatus("⏳ Saving to Hindsight memory...");
    try {
      await axios.post(`${API_BASE}/retain`, {
        contact_name: contactName,
        email: contactEmail, 
        meeting_date: meetingDate,
        notes: notes,
      });
      setRetainStatus("✅ Retained successfully in persistent memory!");
      setNotes("");
    } catch (err) {
      setRetainStatus("❌ Error storing notes: " + err.message);
    }
  };

  const handleSendChat = async () => {
    if (!chatInput.trim()) return;
    
    const userText = chatInput;
    setMessages((prev) => [...prev, { sender: "user", text: userText }]);
    setChatInput("");
    setLoading(true);

    try {
      const res = await axios.post(`${API_BASE}/chat`, { query: userText });
      setMessages((prev) => [...prev, { sender: "ai", text: res.data.reply }]);
      setMemories(res.data.memories);
    } catch (err) {
      setMessages((prev) => [...prev, { sender: "ai", text: "❌ Error connecting to agent." }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <header className="header-container">
        <div>
            <h2>Executive Meeting Prep Agent</h2>
            <p>Persistent Memory powered by Hindsight & Groq</p>
        </div>
        <button onClick={handleReset} className="reset-btn">🔄 Reset Workspace</button>
      </header>

      <div className="grid">
        <div className="card">
          <h3>1. Feed Past Notes (retain)</h3>
          
          <label>Contact Name</label>
          <input type="text" value={contactName} onChange={(e) => setContactName(e.target.value)} placeholder="E.g., Ananya Desai" />
          
          <label>Contact Email ID</label>
          <input type="email" value={contactEmail} onChange={(e) => setContactEmail(e.target.value)} placeholder="E.g., ananya@techcorp.com" />

          <label>Meeting Date</label>
          <input type="date" value={meetingDate} onChange={(e) => setMeetingDate(e.target.value)} />
          
          <label>Discussion & Commitments</label>
          <textarea rows="5" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Enter meeting notes here..." />
          
          <button onClick={handleRetain}>Store into Memory</button>
          {retainStatus && <p className="status">{retainStatus}</p>}
        </div>

       
        <div className="card chat-card">
          <h3>2. Chat with Agent (reflect)</h3>
          <div className="chat-window">
            {messages.map((msg, index) => (
              <div key={index} className={`message-row ${msg.sender}`}>
                <div className={`bubble ${msg.sender}`}>{msg.text}</div>
              </div>
            ))}
            {loading && <div className="message-row ai"><div className="bubble ai">Recalling Memory...</div></div>}
          </div>
          
          <div className="chat-input-area">
            <input 
              type="text" 
              value={chatInput} 
              onChange={(e) => setChatInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSendChat()}
              placeholder="E.g., Prepare me for my call with Rajesh..."
            />
            <button onClick={handleSendChat} disabled={loading}>Send</button>
          </div>
        </div>
      </div>

      <div className="card memory-card">
        <h3>🧠 Hindsight Live Memory Inspector</h3>
        <pre>{memories ? JSON.stringify(memories, null, 2) : "No memories recalled yet..."}</pre>
      </div>
    </div>
  );
}

export default App;