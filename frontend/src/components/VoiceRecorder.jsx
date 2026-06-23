import React, { useState, useRef, useEffect } from 'react';
import { Mic, Square, Play, AlertCircle, RefreshCw } from 'lucide-react';

export default function AudioRecorder({ session_id, onUploadSuccess, backendUrl }) {
  const [isRecording, setIsRecording] = useState(false);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioUrl, setAudioUrl] = useState(null);
  const [recordingTime, setRecordingTime] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [error, setError] = useState(null);
  
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, []);

  const startRecording = async () => {
    audioChunksRef.current = [];
    setAudioBlob(null);
    setAudioUrl(null);
    setError(null);
    setRecordingTime(0);

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const audioUrl = URL.createObjectURL(audioBlob);
        setAudioBlob(audioBlob);
        setAudioUrl(audioUrl);
        
        // Stop all tracks on the stream to release mic icon
        stream.getTracks().forEach(track => track.stop());
      };

      mediaRecorder.start();
      setIsRecording(true);
      
      timerRef.current = setInterval(() => {
        setRecordingTime((prev) => prev + 1);
      }, 1000);

    } catch (err) {
      console.error("Error accessing microphone:", err);
      setError("Microphone access denied or not available. Please allow mic permissions.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };

  const uploadAudio = async () => {
    if (!audioBlob) return;
    setIsUploading(true);
    setError(null);

    const formData = new FormData();
    formData.append('session_id', session_id);
    // Name it voice.webm so backend handles it nicely
    formData.append('file', audioBlob, 'voice.webm');

    try {
      const response = await fetch(`${backendUrl}/api/upload-voice`, {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed with status ${response.status}`);
      }

      const data = await response.json();
      onUploadSuccess(data);
      // Reset after successful upload
      setAudioBlob(null);
      setAudioUrl(null);
    } catch (err) {
      console.error("Audio upload error:", err);
      setError("Failed to upload audio to server.");
    } finally {
      setIsUploading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', width: '100%' }}>
      <div style={{
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        padding: '12px 16px',
        borderRadius: '12px',
        background: 'rgba(255, 255, 255, 0.03)',
        border: '1px solid rgba(255, 255, 255, 0.05)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isRecording ? (
            <button 
              onClick={stopRecording}
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: 'var(--color-danger)',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
              }}
              title="Stop Recording"
            >
              <Square size={18} fill="white" />
            </button>
          ) : (
            <button 
              onClick={startRecording}
              style={{
                width: '40px',
                height: '40px',
                borderRadius: '50%',
                background: 'var(--color-accent-indigo)',
                border: 'none',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                boxShadow: '0 4px 14px rgba(99, 102, 241, 0.4)',
              }}
              title="Start Recording"
              disabled={isUploading}
            >
              <Mic size={18} />
            </button>
          )}
          
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span style={{ fontSize: '14px', fontWeight: '500' }}>
              {isRecording ? "Recording Voice Note..." : audioBlob ? "Recording Completed" : "Record voice note"}
            </span>
            <span style={{ fontSize: '12px', color: 'var(--color-text-secondary)' }}>
              {isRecording ? formatTime(recordingTime) : audioBlob ? "Ready to upload" : "Tap to start mic"}
            </span>
          </div>
        </div>

        {/* Recording active soundwaves */}
        {isRecording && (
          <div className="waveform">
            <div className="wave-bar"></div>
            <div className="wave-bar"></div>
            <div className="wave-bar"></div>
            <div className="wave-bar"></div>
            <div className="wave-bar"></div>
          </div>
        )}

        {/* Audio Player and Upload Option */}
        {audioUrl && !isRecording && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <audio src={audioUrl} controls style={{ height: '36px', width: '180px' }} />
            <button
              onClick={uploadAudio}
              disabled={isUploading}
              style={{
                padding: '8px 14px',
                borderRadius: '8px',
                background: 'var(--color-accent-purple)',
                border: 'none',
                color: 'white',
                fontWeight: '600',
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                fontSize: '13px'
              }}
            >
              {isUploading ? (
                <>
                  <RefreshCw size={14} className="pulse-glow" style={{ animation: 'spin 1s linear infinite' }} />
                  Processing...
                </>
              ) : "Upload Note"}
            </button>
          </div>
        )}
      </div>

      {error && (
        <div style={{ 
          display: 'flex', 
          alignItems: 'center', 
          gap: '8px', 
          color: 'var(--color-danger)', 
          fontSize: '12px',
          padding: '0 4px'
        }}>
          <AlertCircle size={14} />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
