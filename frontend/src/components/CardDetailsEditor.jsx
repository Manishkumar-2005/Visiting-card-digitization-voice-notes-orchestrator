import React, { useState, useEffect } from 'react';
import { User, Building, Mail, Phone, Globe, MapPin, Briefcase, Check, X, RefreshCw } from 'lucide-react';

export default function CardDetailsEditor({ card_data, onApprove, onCancel, isSubmitting }) {
  const [formData, setFormData] = useState({
    name: '',
    company: '',
    title: '',
    email: '',
    phone: '',
    website: '',
    address: ''
  });

  // Sync with prop updates
  useEffect(() => {
    if (card_data) {
      setFormData({
        name: card_data.name || '',
        company: card_data.company || '',
        title: card_data.title || '',
        email: card_data.email || '',
        phone: card_data.phone || '',
        website: card_data.website || '',
        address: card_data.address || ''
      });
    }
  }, [card_data]);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onApprove(formData);
  };

  return (
    <div style={{
      padding: '20px',
      borderRadius: '16px',
      background: 'rgba(99, 102, 241, 0.05)',
      border: '1px solid rgba(99, 102, 241, 0.2)',
      boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
      display: 'flex',
      flexDirection: 'column',
      gap: '16px',
      margin: '12px 0',
      width: '100%',
      maxWidth: '650px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h4 style={{ fontSize: '16px', fontWeight: '700', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ fontSize: '18px' }}>🔍</span> Verify Extracted Card Details
          </h4>
          <p style={{ fontSize: '12px', color: 'var(--color-text-secondary)', marginTop: '4px' }}>
            Verify and make corrections to the OCR output before committing.
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '12px' }}>
          
          {/* Name Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Full Name</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <User size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Company Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Company</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Building size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="text"
                name="company"
                value={formData.company}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Job Title Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Job Title</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Briefcase size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="text"
                name="title"
                value={formData.title}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Email Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Email Address</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Mail size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Phone Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Phone Number</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Phone size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="text"
                name="phone"
                value={formData.phone}
                onChange={handleChange}
                required
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

          {/* Website Field */}
          <div className="input-group">
            <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Website</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Globe size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
              <input
                type="text"
                name="website"
                value={formData.website}
                onChange={handleChange}
                style={{
                  width: '100%',
                  padding: '8px 10px 8px 32px',
                  background: 'rgba(255, 255, 255, 0.03)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: '8px',
                  color: 'white',
                  fontSize: '13px',
                  outline: 'none',
                }}
              />
            </div>
          </div>

        </div>

        {/* Address Field (Spans full width) */}
        <div className="input-group">
          <label style={{ display: 'block', fontSize: '11px', fontWeight: '600', color: 'var(--color-text-secondary)', marginBottom: '4px', textTransform: 'uppercase' }}>Address</label>
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
            <MapPin size={14} style={{ position: 'absolute', left: '10px', color: 'var(--color-accent-indigo)' }} />
            <input
              type="text"
              name="address"
              value={formData.address}
              onChange={handleChange}
              style={{
                width: '100%',
                padding: '8px 10px 8px 32px',
                background: 'rgba(255, 255, 255, 0.03)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: '8px',
                color: 'white',
                fontSize: '13px',
                outline: 'none',
              }}
            />
          </div>
        </div>

        {/* Actions Button */}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '8px' }}>
          <button
            type="button"
            onClick={onCancel}
            disabled={isSubmitting}
            style={{
              padding: '8px 14px',
              borderRadius: '8px',
              background: 'rgba(255, 255, 255, 0.05)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              color: 'var(--color-text-primary)',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px'
            }}
          >
            <X size={14} />
            Discard
          </button>
          
          <button
            type="submit"
            disabled={isSubmitting}
            style={{
              padding: '8px 16px',
              borderRadius: '8px',
              background: 'var(--color-success)',
              border: 'none',
              color: 'white',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: '600',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              boxShadow: '0 4px 14px rgba(16, 185, 129, 0.3)',
            }}
          >
            {isSubmitting ? (
              <>
                <RefreshCw size={14} className="pulse-glow" style={{ animation: 'spin 1s linear infinite' }} />
                Saving...
              </>
            ) : (
              <>
                <Check size={14} />
                Approve & Save
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
