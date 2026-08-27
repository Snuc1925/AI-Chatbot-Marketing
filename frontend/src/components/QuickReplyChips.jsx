import React, { useState } from 'react';
import { Sparkles, Calendar, ArrowRight, Check, Edit3, Send } from 'lucide-react';

export const QuickReplyChips = ({ options = [], text = '', onSelectOption, disabled = false }) => {
  const [showDatePicker, setShowDatePicker] = useState(false);
  const [showCustomInput, setShowCustomInput] = useState(false);
  const [customText, setCustomText] = useState('');
  const [fromDate, setFromDate] = useState('');
  const [toDate, setToDate] = useState('');

  // 1. Determine list of options
  let finalOptions = [];
  if (Array.isArray(options) && options.length > 0) {
    finalOptions = [...options];
  } else if (text) {
    // Fallback: extract square brackets if options not provided from LLM
    const regex = /\[(.*?)\]/g;
    let match;
    while ((match = regex.exec(text)) !== null) {
      const opt = match[1].trim();
      if (opt && !finalOptions.includes(opt)) {
        finalOptions.push(opt);
      }
    }
  }

  // Filter out any accidental 'khác' / 'other' from the main options list since we add it explicitly at the end
  finalOptions = finalOptions.filter(
    (opt) => !['khác', 'tự nhập', 'khác (tự nhập)', 'other', 'khac'].includes(opt.toLowerCase().trim())
  );

  if (finalOptions.length === 0 && !text) return null;

  const handleChipClick = (option) => {
    if (option.toLowerCase().includes('tùy chọn') || option.toLowerCase().includes('tuy chon')) {
      setShowDatePicker(true);
      setShowCustomInput(false);
    } else {
      setShowDatePicker(false);
      setShowCustomInput(false);
      onSelectOption(option);
    }
  };

  const handleOtherClick = () => {
    setShowCustomInput((prev) => !prev);
    setShowDatePicker(false);
  };

  const handleCustomSubmit = (e) => {
    e.preventDefault();
    if (customText.trim()) {
      onSelectOption(customText.trim());
      setCustomText('');
      setShowCustomInput(false);
    }
  };

  const handleDateSubmit = (e) => {
    e.preventDefault();
    if (fromDate && toDate) {
      // Format as DD/MM/YYYY
      const formatViDate = (d) => {
        const [yyyy, mm, dd] = d.split('-');
        return `${dd}/${mm}/${yyyy}`;
      };
      const textResponse = `Từ ngày: ${formatViDate(fromDate)} Đến ngày: ${formatViDate(toDate)}`;
      onSelectOption(textResponse);
      setShowDatePicker(false);
    }
  };

  return (
    <div className="quick-replies-container">
      <div className="quick-replies-label">
        <Sparkles size={13} color="var(--primary)" />
        <span>Gợi ý lựa chọn nhanh:</span>
      </div>

      <div className="chips-wrapper">
        {finalOptions.map((opt, idx) => (
          <button
            key={idx}
            className="chip-btn"
            onClick={() => handleChipClick(opt)}
            disabled={disabled}
            type="button"
          >
            {opt.toLowerCase().includes('ngày') || opt.toLowerCase().includes('tháng') || opt.toLowerCase().includes('hôm nay') ? (
              <Calendar size={13} />
            ) : (
              <ArrowRight size={13} />
            )}
            <span>{opt}</span>
          </button>
        ))}

        {/* Option 'Khác (Tự nhập)' */}
        <button
          className={`chip-btn chip-btn-other ${showCustomInput ? 'active' : ''}`}
          onClick={handleOtherClick}
          disabled={disabled}
          type="button"
          title="Tự nhập câu trả lời khác"
        >
          <Edit3 size={13} />
          <span>Khác (Tự nhập)</span>
        </button>
      </div>

      {/* Inline Custom Input */}
      {showCustomInput && (
        <form className="custom-input-box" onSubmit={handleCustomSubmit}>
          <input
            type="text"
            className="custom-text-input"
            placeholder="Nhập câu trả lời hoặc thông tin khác của bạn..."
            value={customText}
            onChange={(e) => setCustomText(e.target.value)}
            autoFocus
            disabled={disabled}
          />
          <button
            type="submit"
            className="btn-pill"
            style={{ background: 'var(--primary)', color: '#ffffff', borderColor: 'var(--primary)', padding: '6px 14px' }}
            disabled={!customText.trim() || disabled}
          >
            <Send size={13} />
            <span>Gửi</span>
          </button>
        </form>
      )}

      {/* Date Picker Box */}
      {showDatePicker && (
        <form className="date-picker-box" onSubmit={handleDateSubmit}>
          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-main)', width: '100%' }}>
            Chọn khoảng thời gian tùy chọn:
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Từ:</span>
            <input
              type="date"
              className="date-input"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              required
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Đến:</span>
            <input
              type="date"
              className="date-input"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn-pill"
            style={{ background: 'var(--primary)', color: '#ffffff', borderColor: 'var(--primary)' }}
            disabled={!fromDate || !toDate}
          >
            <Check size={13} />
            <span>Gửi khoảng thời gian</span>
          </button>
        </form>
      )}
    </div>
  );
};
