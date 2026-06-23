import React, { useState, useEffect, useRef } from 'react';
import { 
  MessageSquare, Plus, Trash2, Send, Image, Database, BookOpen, 
  Settings, Check, X, RefreshCw, Volume2, ShieldAlert, ArrowRight, UserCheck, AlertTriangle 
} from 'lucide-react';
import VoiceRecorder from './components/VoiceRecorder';
import CardDetailsEditor from './components/CardDetailsEditor';

// In production, Vite can read the URL or default to backend host.
// We fallback to localhost:8000 for local development.
const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

export default function App() {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [appState, setAppState] = useState({
    action_required: 'idle',
    card_data: null,
    is_duplicate: false,
    duplicate_contact: null
  });
  
  // View Toggle: 'chat' | 'database'
  const [activeView, setActiveView] = useState('chat');
  const [contacts, setContacts] = useState([]);
  const [isLoadingContacts, setIsLoadingContacts] = useState(false);
  
  // API Health status
  const [apiStatus, setApiStatus] = useState(null);
  
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  // Initialize: Load sessions and API Health status
  useEffect(() => {
    fetchSessions();
    fetchApiHealth();
  }, []);

  // Fetch messages when active session changes
  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
      // Reset blocking actions when switching sessions
      setAppState({
        action_required: 'idle',
        card_data: null,
        is_duplicate: false,
        duplicate_contact: null
      });
    } else {
      setMessages([]);
    }
  }, [activeSessionId]);

  // Scroll chat to bottom
  useEffect(() => {
    scrollToBottom();
  }, [messages, appState]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const fetchApiHealth = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/`);
      if (response.ok) {
        const data = await response.json();
        setApiStatus(data);
      }
    } catch (err) {
      console.error("API check failed:", err);
    }
  };

  const fetchSessions = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/sessions`);
      if (response.ok) {
        const data = await response.json();
        setSessions(data);
        if (data.length > 0 && !activeSessionId) {
          setActiveSessionId(data[0].id);
        }
      }
    } catch (err) {
      console.error("Failed to fetch sessions:", err);
    }
  };

  const createSession = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: `Session ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}` }),
      });
      if (response.ok) {
        const newSession = await response.json();
        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newSession.id);
        setActiveView('chat');
      }
    } catch (err) {
      console.error("Failed to create session:", err);
    }
  };

  const deleteSession = async (id, e) => {
    e.stopPropagation();
    try {
      const response = await fetch(`${BACKEND_URL}/api/sessions/${id}`, {
        method: 'DELETE',
      });
      if (response.ok) {
        setSessions((prev) => prev.filter((s) => s.id !== id));
        if (activeSessionId === id) {
          const remaining = sessions.filter((s) => s.id !== id);
          setActiveSessionId(remaining.length > 0 ? remaining[0].id : null);
        }
      }
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const fetchMessages = async (sessionId) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/sessions/${sessionId}/messages`);
      if (response.ok) {
        const data = await response.json();
        setMessages(data);
      }
    } catch (err) {
      console.error("Failed to fetch messages:", err);
    }
  };

  const fetchContacts = async () => {
    setIsLoadingContacts(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/contacts`);
      if (response.ok) {
        const data = await response.json();
        setContacts(data);
      }
    } catch (err) {
      console.error("Failed to fetch contacts:", err);
    } finally {
      setIsLoadingContacts(false);
    }
  };

  // Switch between Chat and Contacts Grid
  const toggleView = (view) => {
    setActiveView(view);
    if (view === 'database') {
      fetchContacts();
    }
  };

  // Send standard text message
  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if (!inputText.trim() || !activeSessionId || isSending) return;

    const textToSend = inputText;
    setInputText('');
    setIsSending(true);

    // Append user message locally for immediate UI update
    const tempUserMsg = {
      id: Date.now(),
      sender: 'user',
      content: textToSend,
      msg_type: 'text',
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: textToSend, session_id: activeSessionId }),
      });

      if (response.ok) {
        const data = await response.json();
        setAppState({
          action_required: data.action_required,
          card_data: data.card_data,
          is_duplicate: data.is_duplicate,
          duplicate_contact: data.duplicate_contact
        });
        fetchMessages(activeSessionId);
      }
    } catch (err) {
      console.error("Failed to send message:", err);
    } finally {
      setIsSending(false);
    }
  };

  // Upload image (visiting card)
  const handleCardUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file || !activeSessionId) return;

    setIsSending(true);
    const formData = new FormData();
    formData.append('session_id', activeSessionId);
    formData.append('file', file);

    // Add local indicator message
    const tempUserMsg = {
      id: Date.now(),
      sender: 'user',
      content: `[Uploading Visiting Card: ${file.name}]`,
      msg_type: 'image',
      created_at: new Date().toISOString()
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await fetch(`${BACKEND_URL}/api/upload-card`, {
        method: 'POST',
        body: formData,
      });

      if (response.ok) {
        const data = await response.json();
        setAppState({
          action_required: data.action_required,
          card_data: data.card_data,
          is_duplicate: data.is_duplicate,
          duplicate_contact: data.duplicate_contact
        });
        fetchMessages(activeSessionId);
      }
    } catch (err) {
      console.error("Visiting card upload failed:", err);
    } finally {
      setIsSending(false);
      // Reset input file value
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  // Handle Human-in-the-Loop OCR Approval
  const handleApproveCardDetails = async (verifiedDetails) => {
    setIsSending(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/approve-card`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: activeSessionId,
          card_data: verifiedDetails
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAppState({
          action_required: data.action_required,
          card_data: data.card_data,
          is_duplicate: data.is_duplicate,
          duplicate_contact: data.duplicate_contact
        });
        fetchMessages(activeSessionId);
      }
    } catch (err) {
      console.error("Verification approval failed:", err);
    } finally {
      setIsSending(false);
    }
  };

  // Handle OCR Discard/Cancel
  const handleDiscardCard = async () => {
    setInputText('cancel');
    setTimeout(() => {
      handleSendMessage();
    }, 100);
  };

  // Handle Duplicate Choice Decision
  const handleDuplicateDecision = async (decision) => {
    setIsSending(true);
    try {
      const response = await fetch(`${BACKEND_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: decision,
          session_id: activeSessionId
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setAppState({
          action_required: data.action_required,
          card_data: data.card_data,
          is_duplicate: data.is_duplicate,
          duplicate_contact: data.duplicate_contact
        });
        fetchMessages(activeSessionId);
      }
    } catch (err) {
      console.error("Duplicate choice failed:", err);
    } finally {
      setIsSending(false);
    }
  };

  // Callback on successful voice note upload
  const handleVoiceUploadSuccess = (data) => {
    setAppState({
      action_required: data.action_required,
      card_data: data.card_data,
      is_duplicate: data.is_duplicate,
      duplicate_contact: data.duplicate_contact
    });
    fetchMessages(activeSessionId);
  };

  return (
    <div style={{ display: 'flex', width: '100%', height: '100%' }}>
      {/* Sidebar */}
      <div className="glass-panel" style={{
        width: '320px',
        borderRight: '1px solid var(--glass-border)',
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        zIndex: 10
      }}>
        {/* Sidebar Header */}
        <div style={{ padding: '24px 20px', borderBottom: '1px solid var(--glass-border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontSize: '28px' }}>📇</span>
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <h1 style={{ fontSize: '16px', fontWeight: '700', letterSpacing: '-0.3px', background: 'linear-gradient(90deg, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                CardDigitizer
              </h1>
              <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', fontWeight: '600' }}>Voice Notes Orchestrator</span>
            </div>
          </div>
        </div>

        {/* Navigation View Toggles */}
        <div style={{ padding: '12px 16px', display: 'flex', gap: '8px' }}>
          <button 
            onClick={() => toggleView('chat')}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '10px',
              border: 'none',
              background: activeView === 'chat' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
              color: activeView === 'chat' ? 'white' : 'var(--color-text-secondary)',
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            <MessageSquare size={16} />
            Chat
          </button>
          
          <button 
            onClick={() => toggleView('database')}
            style={{
              flex: 1,
              padding: '10px',
              borderRadius: '10px',
              border: 'none',
              background: activeView === 'database' ? 'rgba(99, 102, 241, 0.15)' : 'transparent',
              color: activeView === 'database' ? 'white' : 'var(--color-text-secondary)',
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              transition: 'all 0.2s'
            }}
          >
            <Database size={16} />
            Contacts
          </button>
        </div>

        {/* Sessions Area (Only shown for Chat view) */}
        {activeView === 'chat' ? (
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
            <div style={{ padding: '8px 16px 12px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '11px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--color-text-muted)', letterSpacing: '0.5px' }}>
                Chat Sessions
              </span>
              <button 
                onClick={createSession}
                style={{
                  background: 'var(--color-accent-indigo)',
                  border: 'none',
                  color: 'white',
                  width: '26px',
                  height: '26px',
                  borderRadius: '6px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer',
                  boxShadow: '0 2px 8px rgba(99, 102, 241, 0.3)',
                }}
              >
                <Plus size={16} />
              </button>
            </div>
            
            <div style={{ flex: 1, overflowY: 'auto', padding: '0 12px 16px 12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {sessions.map((session) => (
                <div 
                  key={session.id}
                  onClick={() => setActiveSessionId(session.id)}
                  style={{
                    padding: '12px 14px',
                    borderRadius: '10px',
                    cursor: 'pointer',
                    background: activeSessionId === session.id ? 'rgba(255, 255, 255, 0.04)' : 'transparent',
                    border: '1px solid',
                    borderColor: activeSessionId === session.id ? 'rgba(255, 255, 255, 0.08)' : 'transparent',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    transition: 'all 0.2s'
                  }}
                  className="session-item"
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px', overflow: 'hidden' }}>
                    <MessageSquare size={15} style={{ color: activeSessionId === session.id ? 'var(--color-accent-indigo)' : 'var(--color-text-muted)' }} />
                    <span style={{ fontSize: '13px', fontWeight: '500', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', color: activeSessionId === session.id ? 'white' : 'var(--color-text-secondary)' }}>
                      {session.name}
                    </span>
                  </div>
                  <button 
                    onClick={(e) => deleteSession(session.id, e)}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--color-text-muted)',
                      cursor: 'pointer',
                      opacity: activeSessionId === session.id ? 1 : 0,
                      transition: 'opacity 0.2s'
                    }}
                    className="delete-session-btn"
                  >
                    <Trash2 size={13} hover-color="var(--color-danger)" />
                  </button>
                </div>
              ))}
              
              {sessions.length === 0 && (
                <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--color-text-muted)', fontSize: '12px' }}>
                  No sessions active. Create one to start.
                </div>
              )}
            </div>
          </div>
        ) : (
          <div style={{ flex: 1, padding: '16px', fontSize: '12px', color: 'var(--color-text-secondary)', display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div className="glass-card" style={{ padding: '12px' }}>
              <h5 style={{ color: 'white', fontWeight: '600', marginBottom: '6px' }}>View Saved Data</h5>
              <p>This view polls the digitized sheet rows. Any accepted visiting cards or voice transcripts show up in real-time here.</p>
            </div>
          </div>
        )}

        {/* Sidebar Footer: Credentials Indicator */}
        <div style={{ padding: '16px', borderTop: '1px solid var(--glass-border)', display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <span style={{ fontSize: '10px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--color-text-muted)' }}>
            System Integrity
          </span>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '11px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Google Sheets API:</span>
              <span style={{ 
                padding: '2px 6px', 
                borderRadius: '4px', 
                fontWeight: '600', 
                fontSize: '9px',
                background: apiStatus?.features?.sheets_configured ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                color: apiStatus?.features?.sheets_configured ? 'var(--color-success)' : 'var(--color-warning)'
              }}>
                {apiStatus?.features?.sheets_configured ? 'LIVE' : 'MOCK'}
              </span>
            </div>
            
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>WhatsApp API:</span>
              <span style={{ 
                padding: '2px 6px', 
                borderRadius: '4px', 
                fontWeight: '600', 
                fontSize: '9px',
                background: apiStatus?.features?.whatsapp_configured ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                color: apiStatus?.features?.whatsapp_configured ? 'var(--color-success)' : 'var(--color-warning)'
              }}>
                {apiStatus?.features?.whatsapp_configured ? 'LIVE' : 'MOCK'}
              </span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>Database (MongoDB):</span>
              <span style={{ 
                padding: '2px 6px', 
                borderRadius: '4px', 
                fontWeight: '600', 
                fontSize: '9px',
                background: apiStatus?.features?.mongodb_configured ? 'rgba(16, 185, 129, 0.15)' : 'rgba(59, 130, 246, 0.15)',
                color: apiStatus?.features?.mongodb_configured ? 'var(--color-success)' : 'var(--color-accent-blue)'
              }}>
                {apiStatus?.features?.mongodb_configured ? 'MONGODB' : 'SQLITE'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' }}>
        
        {/* Active View: Chat */}
        {activeView === 'chat' && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', overflow: 'hidden' }}>
            
            {/* Header */}
            <div className="glass-panel" style={{ 
              padding: '16px 24px', 
              borderBottom: '1px solid var(--glass-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h2 style={{ fontSize: '15px', fontWeight: '700' }}>
                  {sessions.find((s) => s.id === activeSessionId)?.name || 'Select a session'}
                </h2>
                <p style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  {activeSessionId ? `Session ID: ${activeSessionId}` : 'Create a session in the left sidebar to start'}
                </p>
              </div>
              
              {appState.status_message && activeSessionId && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12px',
                  background: 'rgba(255, 255, 255, 0.04)',
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: '1px solid rgba(255, 255, 255, 0.05)'
                }}>
                  <span className="pulse-glow" style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--color-accent-indigo)' }}></span>
                  <span style={{ color: 'var(--color-text-secondary)', fontWeight: '500' }}>{appState.status_message}</span>
                </div>
              )}
            </div>

            {/* Chat Messages Feed */}
            {activeSessionId ? (
              <div style={{ flex: 1, overflowY: 'auto', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                
                {/* Intro message if feed empty */}
                {messages.length === 0 && (
                  <div style={{
                    margin: 'auto',
                    maxWidth: '450px',
                    textAlign: 'center',
                    padding: '40px 20px',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '16px'
                  }}>
                    <span style={{ fontSize: '48px' }}>👋</span>
                    <h3 style={{ fontSize: '18px', fontWeight: '700' }}>Visiting Card Orchestrator</h3>
                    <p style={{ fontSize: '13px', color: 'var(--color-text-secondary)', lineHeight: '1.6' }}>
                      Ready to digitize a card? Upload a visiting card image to begin, or drop details in the text input box. After saving a contact, you can upload voice notes to update notes or fields automatically!
                    </p>
                    <button
                      onClick={() => fileInputRef.current?.click()}
                      style={{
                        padding: '10px 18px',
                        borderRadius: '10px',
                        background: 'linear-gradient(135deg, var(--color-accent-indigo), var(--color-accent-purple))',
                        border: 'none',
                        color: 'white',
                        fontWeight: '600',
                        fontSize: '13px',
                        cursor: 'pointer',
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        boxShadow: '0 4px 18px rgba(99, 102, 241, 0.3)'
                      }}
                    >
                      <Image size={16} />
                      Upload Visiting Card
                    </button>
                  </div>
                )}

                {/* Messages mapping */}
                {messages.map((msg) => {
                  const isUser = msg.sender === 'user';
                  return (
                    <div 
                      key={msg.id}
                      style={{
                        display: 'flex',
                        justifyContent: isUser ? 'flex-end' : 'flex-start',
                        width: '100%',
                      }}
                    >
                      <div style={{
                        maxWidth: '70%',
                        padding: '12px 16px',
                        borderRadius: '16px',
                        borderTopRightRadius: isUser ? '4px' : '16px',
                        borderTopLeftRadius: !isUser ? '4px' : '16px',
                        background: isUser ? 'var(--color-accent-indigo)' : 'rgba(255,255,255,0.03)',
                        border: isUser ? 'none' : '1px solid rgba(255,255,255,0.05)',
                        color: 'white',
                        fontSize: '13.5px',
                        lineHeight: '1.5',
                        whiteSpace: 'pre-line',
                        boxShadow: isUser ? '0 4px 12px rgba(99, 102, 241, 0.2)' : 'none',
                        position: 'relative'
                      }}>
                        {/* Audio attachment display */}
                        {msg.msg_type === 'audio' && msg.metadata?.file_url && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'rgba(255,255,255,0.7)' }}>
                              <Volume2 size={12} />
                              <span>Audio Note Attached</span>
                            </div>
                            <audio src={`${BACKEND_URL}${msg.metadata.file_url}`} controls style={{ height: '32px', width: '220px' }} />
                          </div>
                        )}
                        
                        {/* Image attachment display */}
                        {msg.msg_type === 'image' && msg.metadata?.file_url && (
                          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '8px' }}>
                            <img 
                              src={`${BACKEND_URL}${msg.metadata.file_url}`} 
                              alt="Visiting card attachment" 
                              style={{ 
                                maxWidth: '100%', 
                                maxHeight: '180px', 
                                borderRadius: '8px', 
                                border: '1px solid rgba(255,255,255,0.15)' 
                              }} 
                            />
                          </div>
                        )}

                        {/* Message content text */}
                        {msg.content}
                        
                        {/* Timestamp */}
                        <div style={{ 
                          fontSize: '9px', 
                          color: isUser ? 'rgba(255,255,255,0.5)' : 'var(--color-text-muted)', 
                          textAlign: 'right', 
                          marginTop: '6px' 
                        }}>
                          {new Date(msg.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                        </div>
                      </div>
                    </div>
                  );
                })}

                {/* Human-in-the-loop Card Inspector Card */}
                {appState.action_required === 'awaiting_ocr_approval' && appState.card_data && (
                  <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start' }}>
                    <CardDetailsEditor 
                      card_data={appState.card_data}
                      onApprove={handleApproveCardDetails}
                      onCancel={handleDiscardCard}
                      isSubmitting={isSending}
                    />
                  </div>
                )}

                {/* Duplicates block selection */}
                {appState.action_required === 'awaiting_duplicate_choice' && (
                  <div style={{ display: 'flex', width: '100%', justifyContent: 'flex-start' }}>
                    <div style={{
                      padding: '20px',
                      borderRadius: '16px',
                      background: 'rgba(245, 158, 11, 0.05)',
                      border: '1px solid rgba(245, 158, 11, 0.2)',
                      boxShadow: '0 8px 32px rgba(0,0,0,0.15)',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '12px',
                      maxWidth: '480px',
                    }}>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <AlertTriangle size={20} style={{ color: 'var(--color-warning)', flexShrink: 0 }} />
                        <div>
                          <h4 style={{ fontSize: '14px', fontWeight: '700', color: 'white' }}>Duplicate Contact Decision</h4>
                          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px', lineHeight: '1.4' }}>
                            A record exists with the same email or phone number. What action would you like to perform?
                          </p>
                        </div>
                      </div>
                      
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end', marginTop: '6px' }}>
                        <button
                          onClick={() => handleDuplicateDecision('cancel')}
                          disabled={isSending}
                          style={{
                            padding: '8px 14px',
                            borderRadius: '8px',
                            background: 'rgba(255, 255, 255, 0.05)',
                            border: '1px solid rgba(255, 255, 255, 0.1)',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '12.5px',
                            fontWeight: '600'
                          }}
                        >
                          Discard
                        </button>
                        
                        <button
                          onClick={() => handleDuplicateDecision('update')}
                          disabled={isSending}
                          style={{
                            padding: '8px 14px',
                            borderRadius: '8px',
                            background: 'var(--color-warning)',
                            border: 'none',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '12.5px',
                            fontWeight: '600',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '4px',
                            boxShadow: '0 4px 10px rgba(245, 158, 11, 0.25)'
                          }}
                        >
                          <UserCheck size={14} />
                          Overwrite & Log
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ textAlign: 'center', color: 'var(--color-text-muted)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px' }}>
                  <span style={{ fontSize: '40px' }}>📁</span>
                  <p style={{ fontSize: '14px', fontWeight: '500' }}>Please select or create a session in the left panel to begin.</p>
                </div>
              </div>
            )}

            {/* Input / Control Bar */}
            {activeSessionId && (
              <div className="glass-panel" style={{ 
                padding: '16px 24px', 
                borderTop: '1px solid var(--glass-border)',
                background: 'rgba(10, 12, 16, 0.9)',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
                zIndex: 5
              }}>
                {/* Voice note recorder widget */}
                <VoiceRecorder 
                  session_id={activeSessionId}
                  backendUrl={BACKEND_URL}
                  onUploadSuccess={handleVoiceUploadSuccess}
                />

                {/* Text and Image Form Input */}
                <form onSubmit={handleSendMessage} style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                  {/* Invisible Image input */}
                  <input 
                    type="file" 
                    ref={fileInputRef} 
                    onChange={handleCardUpload} 
                    accept="image/*"
                    style={{ display: 'none' }} 
                  />
                  
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    disabled={isSending || appState.action_required !== 'idle'}
                    style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '10px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: 'var(--color-text-secondary)',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      transition: 'all 0.2s',
                    }}
                    title="Upload visiting card"
                  >
                    <Image size={18} />
                  </button>

                  <input
                    type="text"
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder={
                      appState.action_required !== 'idle'
                        ? "Graph blocked awaiting action..."
                        : "Ask about saved cards, edit data, or just type a prompt..."
                    }
                    disabled={isSending || appState.action_required !== 'idle'}
                    style={{
                      flex: 1,
                      height: '42px',
                      padding: '0 16px',
                      borderRadius: '10px',
                      background: 'rgba(255,255,255,0.03)',
                      border: '1px solid rgba(255,255,255,0.08)',
                      color: 'white',
                      fontSize: '13px',
                      outline: 'none',
                    }}
                  />

                  <button
                    type="submit"
                    disabled={isSending || !inputText.trim() || appState.action_required !== 'idle'}
                    style={{
                      width: '42px',
                      height: '42px',
                      borderRadius: '10px',
                      background: 'var(--color-accent-indigo)',
                      border: 'none',
                      color: 'white',
                      cursor: 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      boxShadow: '0 4px 10px rgba(99, 102, 241, 0.3)',
                      transition: 'all 0.2s',
                    }}
                  >
                    <Send size={16} />
                  </button>
                </form>
              </div>
            )}
          </div>
        )}

        {/* Active View: Contacts Database Grid */}
        {activeView === 'database' && (
          <div style={{ display: 'flex', flexDirection: 'column', height: '100%', width: '100%', overflow: 'hidden' }}>
            
            {/* Header */}
            <div className="glass-panel" style={{ 
              padding: '16px 24px', 
              borderBottom: '1px solid var(--glass-border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <div>
                <h2 style={{ fontSize: '15px', fontWeight: '700' }}>Digitized Contacts Directory</h2>
                <p style={{ fontSize: '11px', color: 'var(--color-text-secondary)', marginTop: '2px' }}>
                  Sync status: Real-time mirror of Google Sheets / local database.
                </p>
              </div>
              
              <button
                onClick={fetchContacts}
                disabled={isLoadingContacts}
                style={{
                  padding: '8px 14px',
                  borderRadius: '8px',
                  background: 'rgba(255,255,255,0.04)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  color: 'white',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '12.5px',
                  fontWeight: '600'
                }}
              >
                <RefreshCw size={14} className={isLoadingContacts ? 'pulse-glow' : ''} style={{ animation: isLoadingContacts ? 'spin 1s linear infinite' : 'none' }} />
                Sync Sheets
              </button>
            </div>

            {/* Contacts Table/Grid Container */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
              {isLoadingContacts ? (
                <div style={{ display: 'flex', height: '100%', width: '100%', alignItems: 'center', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
                    <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite', color: 'var(--color-accent-indigo)' }} />
                    <span style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>Synchronizing contacts with Google Sheets...</span>
                  </div>
                </div>
              ) : contacts.length > 0 ? (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '16px' }}>
                  {contacts.map((contact, idx) => (
                    <div 
                      key={idx} 
                      className="glass-card" 
                      style={{ 
                        padding: '20px', 
                        display: 'flex', 
                        flexDirection: 'column', 
                        gap: '12px',
                        background: 'rgba(255,255,255,0.01)',
                      }}
                    >
                      {/* Name / Company */}
                      <div>
                        <h4 style={{ fontSize: '15px', fontWeight: '700', color: 'white' }}>{contact.name || 'No Name'}</h4>
                        <span style={{ 
                          fontSize: '11px', 
                          color: 'var(--color-accent-indigo)', 
                          fontWeight: '600',
                          background: 'rgba(99, 102, 241, 0.1)',
                          padding: '2px 6px',
                          borderRadius: '4px',
                          marginTop: '4px',
                          display: 'inline-block'
                        }}>
                          {contact.company || 'Private'}
                        </span>
                      </div>

                      {/* Contact items */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '12px', color: 'var(--color-text-secondary)', borderBottom: '1px solid rgba(255,255,255,0.04)', paddingBottom: '12px' }}>
                        {contact.title && <div>💼 {contact.title}</div>}
                        {contact.email && <div>✉️ {contact.email}</div>}
                        {contact.phone && <div>📞 {contact.phone}</div>}
                        {contact.website && <div>🌐 <a href={contact.website.startsWith('http') ? contact.website : `https://${contact.website}`} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--color-accent-blue)', textDecoration: 'none' }}>{contact.website}</a></div>}
                        {contact.address && <div>📍 {contact.address}</div>}
                      </div>

                      {/* Notes / Audio notes */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px' }}>
                        <div>
                          <span style={{ fontWeight: '700', color: 'white', display: 'block', marginBottom: '4px' }}>Voice Notes</span>
                          <p style={{ color: 'var(--color-text-secondary)', fontStyle: 'italic', lineHeight: '1.4' }}>
                            {contact.notes || "No extra notes logged yet."}
                          </p>
                        </div>
                        
                        {contact.audio_url && (
                          <div style={{ marginTop: '4px' }}>
                            <span style={{ fontSize: '10px', color: 'var(--color-text-muted)', display: 'block', marginBottom: '4px' }}>Attached Audio URL</span>
                            <audio src={`${BACKEND_URL}${contact.audio_url}`} controls style={{ height: '28px', width: '100%' }} />
                          </div>
                        )}
                      </div>

                      <div style={{ fontSize: '10px', color: 'var(--color-text-muted)', textAlign: 'right', marginTop: 'auto' }}>
                        Logged: {new Date(contact.created_at).toLocaleDateString()}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: 'flex', height: '100%', width: '100%', alignItems: 'center', justifyContent: 'center', minHeight: '300px' }}>
                  <div style={{ textAlign: 'center', color: 'var(--color-text-muted)' }}>
                    <span style={{ fontSize: '40px' }}>🗃️</span>
                    <p style={{ fontSize: '14px', marginTop: '8px' }}>No contacts logged yet. Digitize your first card in Chat view!</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
