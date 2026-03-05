import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, User, Mail, Phone, Award } from 'lucide-react';

interface Match {
  user_id: number;
  rank: number;
  name: string;
  email?: string;
  phone?: string;
  skills?: string[];
  match_score: number;
  match_reason: string;
  profile_image_url?: string;
  is_verified?: boolean;
}

interface ChatMessage {
  type: 'user' | 'agent';
  text: string;
  matches?: Match[];
  timestamp: Date;
  quickResponses?: string[];
}

interface ChatResponse {
  agent_response: string;
  requirement_count: number;
  is_complete: boolean;
  quick_responses: string[];
  current_phase: string | null;
  matches: Match[];
}

interface ProfileSearchProps {
  userId?: number;
  onProfileClick?: (profileId: number) => void;
}

export const ProfileSearch: React.FC<ProfileSearchProps> = ({
  userId,
  onProfileClick,
}) => {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Initialize chat on component mount
  useEffect(() => {
    const id = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(id);
    initializeChat(id);
  }, [userId]);

  const initializeChat = async (sessionId: string) => {
    try {
      setLoading(true);
      setError(null);
      
      // Send initial "hi" message
      const response = await fetch('/api/chat-adk/message', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          message: 'hi',
          user_id: userId || 1,
          session_id: sessionId,
          conversation_history: [],
        }),
      });

      if (!response.ok) {
        throw new Error(`Chat initialization failed: ${response.statusText}`);
      }

      const chatData: ChatResponse = await response.json();
      
      // Display agent greeting
      const agentMessage: ChatMessage = {
        type: 'agent',
        text: chatData.agent_response,
        timestamp: new Date(),
        quickResponses: chatData.quick_responses,
      };
      setMessages([agentMessage]);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Failed to initialize chat';
      setError(errorMsg);
      console.error('Chat initialization error:', err);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (messageText: string) => {
    if (!messageText.trim() || !sessionId) return;

    try {
      setLoading(true);
      setError(null);

      // Add user message to chat
      const userMessage: ChatMessage = {
        type: 'user',
        text: messageText,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, userMessage]);

      // Send to chat API
      const response = await fetch('/api/chat-adk/message', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          message: messageText,
          user_id: userId || 1,
          session_id: sessionId,
          conversation_history: [],
        }),
      });

      if (!response.ok) {
        throw new Error('Chat request failed');
      }

      const chatData: ChatResponse = await response.json();

      // Add agent message to chat
      const agentMessage: ChatMessage = {
        type: 'agent',
        text: chatData.agent_response,
        matches: chatData.matches && chatData.matches.length > 0 ? chatData.matches : undefined,
        timestamp: new Date(),
        quickResponses: chatData.quick_responses,
      };
      setMessages((prev) => [...prev, agentMessage]);

      // Clear input
      setInputValue('');
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Chat failed';
      setError(errorMsg);

      const errorMessage: ChatMessage = {
        type: 'agent',
        text: `Sorry, I encountered an error: ${errorMsg}. Please try again.`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim()) {
      sendMessage(inputValue);
    }
  };

  const handleQuickResponse = (response: string) => {
    sendMessage(response);
  };

  const getProfileColor = (index: number) => {
    const colors = [
      'from-blue-400 to-blue-600',
      'from-purple-400 to-purple-600',
      'from-pink-400 to-pink-600',
      'from-green-400 to-green-600',
    ];
    return colors[index % colors.length];
  };

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-lg">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-800 text-white p-6 rounded-t-lg">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Smart Candidate Finder</h1>
        </div>
        <p className="text-blue-100 mt-2">
          Chat with our AI to find perfect candidates for your role
        </p>
      </div>

      {/* Chat Messages Container */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.type === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-2xl ${
                msg.type === 'user'
                  ? 'bg-blue-600 text-white rounded-br-none'
                  : 'bg-gray-100 text-gray-800 rounded-bl-none'
              } rounded-lg p-4 shadow-sm`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.text}</p>

              {/* Profile Matches */}
              {msg.matches && msg.matches.length > 0 && (
                <div className="mt-4 space-y-3">
                  <p className="text-xs font-semibold text-gray-600 mb-2">
                    Found {msg.matches.length} candidate{msg.matches.length !== 1 ? 's' : ''}:
                  </p>
                  {msg.matches.map((match, matchIdx) => (
                    <div
                      key={match.user_id}
                      className="bg-white rounded-lg p-4 cursor-pointer hover:shadow-md transition"
                      onClick={() => onProfileClick?.(match.user_id)}
                    >
                      <div className="flex items-start gap-4">
                        {/* Profile Avatar */}
                        <div className="flex-shrink-0">
                          <div
                            className={`w-16 h-16 rounded-full bg-gradient-to-br ${getProfileColor(
                              matchIdx
                            )} flex items-center justify-center flex-shrink-0`}
                          >
                            {match.profile_image_url ? (
                              <img
                                src={match.profile_image_url}
                                alt={match.name}
                                className="w-full h-full rounded-full object-cover"
                              />
                            ) : (
                              <User size={32} className="text-white" />
                            )}
                          </div>
                          <div className="mt-2 text-center">
                            <span className="text-2xl font-bold text-gray-700">
                              #{match.rank}
                            </span>
                          </div>
                        </div>

                        {/* Profile Info */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h3 className="text-lg font-semibold text-gray-800">
                              {match.name}
                            </h3>
                            {match.is_verified && (
                              <Award size={16} className="text-green-600" />
                            )}
                          </div>

                          {/* Match Score */}
                          <div className="mb-3">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 bg-gray-300 rounded-full h-2 overflow-hidden">
                                <div
                                  className="bg-green-500 h-full transition-all"
                                  style={{
                                    width: `${Math.round(
                                      match.match_score * 100
                                    )}%`,
                                  }}
                                />
                              </div>
                              <span className="text-sm font-semibold text-gray-700 min-w-fit">
                                {Math.round(match.match_score * 100)}% match
                              </span>
                            </div>
                          </div>

                          {/* Match Reason */}
                          <p className="text-sm text-gray-600 italic mb-3">
                            💡 {match.match_reason}
                          </p>

                          {/* Contact Info */}
                          {(match.email || match.phone) && (
                            <div className="flex gap-4 mb-3 text-sm">
                              {match.email && (
                                <button
                                  className="flex items-center gap-1 text-blue-600 hover:underline"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.location.href = `mailto:${match.email}`;
                                  }}
                                >
                                  <Mail size={16} /> {match.email}
                                </button>
                              )}
                              {match.phone && (
                                <button
                                  className="flex items-center gap-1 text-blue-600 hover:underline"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    window.location.href = `tel:${match.phone}`;
                                  }}
                                >
                                  <Phone size={16} /> {match.phone}
                                </button>
                              )}
                            </div>
                          )}

                          {/* Skills */}
                          {match.skills && match.skills.length > 0 && (
                            <div className="flex gap-2 flex-wrap">
                              {match.skills.slice(0, 3).map((skill, skillIdx) => (
                                <span
                                  key={skillIdx}
                                  className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded"
                                >
                                  {skill}
                                </span>
                              ))}
                              {match.skills.length > 3 && (
                                <span className="text-xs text-gray-500">
                                  +{match.skills.length - 3}
                                </span>
                              )}
                            </div>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Quick Responses */}
              {msg.quickResponses && msg.quickResponses.length > 0 && (
                <div className="mt-4 space-y-2">
                  <p className="text-xs font-semibold text-gray-600">Suggested responses:</p>
                  <div className="flex flex-wrap gap-2">
                    {msg.quickResponses.map((response, responseIdx) => (
                      <button
                        key={responseIdx}
                        onClick={() => handleQuickResponse(response)}
                        disabled={loading}
                        className="text-xs bg-gray-200 hover:bg-gray-300 disabled:opacity-50 text-gray-800 px-3 py-2 rounded-full transition"
                      >
                        {response}
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg p-4 flex items-center gap-2">
              <Loader size={20} className="animate-spin text-blue-600" />
              <span className="text-gray-600">Thinking...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="border-t p-4 space-y-2">
        {error && (
          <div className="text-sm text-red-600 bg-red-50 p-2 rounded">
            {error}
          </div>
        )}

        <form onSubmit={handleSendMessage} className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="Tell me about the role you're looking for..."
            disabled={loading}
            className="flex-1 px-4 py-3 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
          />
          <button
            type="submit"
            disabled={loading || !inputValue.trim()}
            className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white px-6 py-3 rounded-lg transition flex items-center gap-2"
          >
            {loading ? (
              <Loader size={20} className="animate-spin" />
            ) : (
              <Send size={20} />
            )}
          </button>
        </form>

        <p className="text-xs text-gray-500">
          💡 Describe the position, required experience, and skills. I'll find the best candidates for you!
        </p>
      </div>
    </div>
  );
};
