import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Input, List, Empty, Modal, Select, message } from 'antd';
import type { InputRef } from 'antd';
import {
  SendOutlined,
  SaveOutlined,
  LoadingOutlined,
  CaretDownOutlined,
  SyncOutlined,
  MenuOutlined,
  BulbOutlined,
} from '@ant-design/icons';
import { wsService, type ChatMessage } from '../services/websocket';
import { useAuthStore } from '../stores/useAuthStore';
import { campaignAPI, characterAPI, saveAPI } from '../services/api';
import type { Campaign, Character, Save } from '../services/api';
import { useTheme } from '../hooks/useTheme';
import { PRESETS } from '../data/presets';
import './ChatRoom.css';

interface ThinkingMessage extends ChatMessage {
  collapsed?: boolean;
}

const QUICK_DICE = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100'];

/** Derive contextual suggestion chips from the KP's response text */
function deriveSuggestions(content: string): string[] {
  const lower = content.toLowerCase();
  const suggestions: string[] = [];

  if (lower.includes('检定') || lower.includes('dc') || lower.includes('掷骰')) {
    suggestions.push('掷骰进行检定');
  }
  if (lower.includes('观察') || lower.includes('侦查') || lower.includes('察觉') || lower.includes('搜索')) {
    suggestions.push('我仔细观察周围环境');
  }
  if (lower.includes('对话') || lower.includes('交谈') || lower.includes('询问') || lower.includes('打听')) {
    suggestions.push('我上前与对方交谈');
  }
  if (lower.includes('门') || lower.includes('房间') || lower.includes('前进') || lower.includes('探索')) {
    suggestions.push('我继续向前探索');
  }
  if (lower.includes('物品') || lower.includes('检查') || lower.includes('调查') || lower.includes('搜查')) {
    suggestions.push('我仔细检查这个物品');
  }
  if (lower.includes('战斗') || lower.includes('攻击') || lower.includes('怪物') || lower.includes('敌人')) {
    suggestions.push('我准备武器迎战');
  }
  if (lower.includes('潜行') || lower.includes('隐藏') || lower.includes('悄悄') || lower.includes('躲')) {
    suggestions.push('我尝试潜行靠近');
  }
  if (lower.includes('法术') || lower.includes('施法') || lower.includes('魔法') || lower.includes('咒语')) {
    suggestions.push('我施展法术');
  }

  // Fallback — always provide some actions
  suggestions.push('我环顾四周寻找线索');
  suggestions.push('我查看身上的装备和物品');
  suggestions.push('我向KP询问更多细节');

  // Deduplicate and limit
  const unique = [...new Set(suggestions)];
  return unique.slice(0, 5);
}

export function ChatRoom() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const { isDark, toggle: toggleTheme } = useTheme();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [messages, setMessages] = useState<ThinkingMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [connected, setConnected] = useState(false);
  const [saves, setSaves] = useState<Save[]>([]);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [diceOverlay, setDiceOverlay] = useState<{ die: string; result: number; max: number } | null>(null);
  const [usedSuggestions, setUsedSuggestions] = useState<Set<string>>(new Set());
  const [isKPThinking, setIsKPThinking] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<InputRef>(null);
  const skipBackendInitRef = useRef(true);
  const usePresetRef = useRef(false);
  const presetSuggestionsRef = useRef<string[]>([]);

  const loadCampaign = async () => {
    try {
      const res = await campaignAPI.get(Number(campaignId));
      setCampaign(res.data);

      // Check if this campaign uses a preset system prompt
      const preset = PRESETS.find(p => p.systemPrompt === res.data.system_prompt);
      if (preset) {
        usePresetRef.current = true;
        const now = new Date().toISOString();
        const openingMsgs: ThinkingMessage[] = preset.opening.map((o, i) => ({
          id: `preset-opening-${i}`,
          type: o.type === 'system' ? 'system' : 'kp_response',
          role: o.type === 'system' ? 'system' : 'kp',
          content: o.text,
          timestamp: now,
        }));
        setMessages(openingMsgs);
        const kpOpening = preset.opening.find(o => o.type === 'ai');
        if (kpOpening?.suggestions) {
          presetSuggestionsRef.current = kpOpening.suggestions;
        }
      } else {
        skipBackendInitRef.current = false;
      }
    } catch {
      message.error('加载战役失败');
    }
  };

  const loadCharacters = async () => {
    try {
      const res = await characterAPI.list();
      setCharacters(res.data);
      if (res.data.length > 0) {
        setSelectedCharacter(res.data[0]);
      }
    } catch {
      message.error('加载角色卡失败');
    }
  };

  const loadSaves = async () => {
    try {
      const res = await saveAPI.list(Number(campaignId));
      setSaves(res.data);
    } catch {
      console.error('加载存档失败');
    }
  };

  const handleOnMessage = useCallback((msg: ChatMessage) => {
    // Skip backend-generated initial messages when using preset opening
    if (skipBackendInitRef.current) {
      if (msg.type === 'system' || msg.type === 'kp_thinking' || msg.type === 'kp_thinking_chunk') {
        return;
      }
      if (msg.type === 'kp_response') {
        skipBackendInitRef.current = false;
        setIsKPThinking(false);
        if (usePresetRef.current) return;
        // For custom campaigns, fall through to normal processing
      }
      if (msg.type === 'player_message' || msg.type === 'dice_result') {
        skipBackendInitRef.current = false;
      }
    }

    if (msg.type === 'history_clear') {
      setMessages([]);
      setUsedSuggestions(new Set());
    } else if (msg.type === 'kp_thinking_chunk') {
      setMessages((prev) =>
        prev.map((m) =>
          m.id === msg.id ? { ...m, content: (m.content || '') + msg.content } : m
        )
      );
    } else if (msg.type === 'kp_response') {
      setIsKPThinking(false);
      // Clear preset suggestions once backend takes over
      presetSuggestionsRef.current = [];
      if (msg.thinking_id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msg.thinking_id
              ? { ...m, type: 'kp_response', role: 'kp', content: msg.content, collapsed: false }
              : m
          )
        );
      } else {
        setMessages((prev) => [...prev, msg]);
      }
      // Reset suggestion state for new KP message
      setUsedSuggestions(new Set());
    } else if (
      msg.type === 'player_message' ||
      msg.type === 'dice_result'
    ) {
      setMessages((prev) => [...prev, msg]);
    } else if (msg.type === 'kp_thinking') {
      setIsKPThinking(true);
      setMessages((prev) => [
        ...prev,
        { ...msg, role: 'kp', timestamp: new Date().toISOString(), collapsed: false },
      ]);
    } else if (msg.type === 'system' || msg.type === 'error') {
      setMessages((prev) => [
        ...prev,
        { type: 'system', role: 'system', content: msg.content, timestamp: new Date().toISOString() },
      ]);
    } else if (msg.type === 'save_loaded') {
      message.success(msg.content);
    }
  }, []);

  const connectWebSocket = useCallback(async () => {
    try {
      await wsService.connect(Number(campaignId), token!);
      wsService.onMessage(handleOnMessage);
      setConnected(true);
    } catch {
      message.error('连接聊天服务器失败');
    }
  }, [campaignId, token, handleOnMessage]);

  useEffect(() => {
    if (!token || !campaignId) {
      navigate('/login');
      return;
    }

    loadCampaign();
    loadCharacters();
    loadSaves();
    connectWebSocket();

    return () => {
      wsService.disconnect();
    };
  }, [campaignId, token, connectWebSocket, navigate]);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleToggleThinking = useCallback((msgId: string) => {
    setMessages((prev) =>
      prev.map((m) => (m.id === msgId ? { ...m, collapsed: !m.collapsed } : m))
    );
  }, []);

  const handleSend = () => {
    if (!inputValue.trim() || !connected) return;
    wsService.sendPlayerMessage(inputValue);
    setInputValue('');
    setIsKPThinking(true);
    inputRef.current?.focus();
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
    setUsedSuggestions(prev => new Set(prev).add(suggestion));
    inputRef.current?.focus();
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickRoll = (diceStr: string) => {
    if (!connected) return;
    const max = parseInt(diceStr.replace('d', ''), 10);
    const result = Math.floor(Math.random() * max) + 1;
    setDiceOverlay({ die: diceStr, result, max });
    setTimeout(() => setDiceOverlay(null), 2500);
    wsService.sendRollDice(diceStr);
  };

  const handleSaveGame = async () => {
    if (!saveName.trim()) {
      message.warning('请输入存档名称');
      return;
    }

    try {
      const snapshot = {
        campaign_id: Number(campaignId),
        session_number: campaign?.current_session || 1,
        character_name: selectedCharacter?.name,
        messages_count: messages.length,
      };
      await saveAPI.create(Number(campaignId), {
        name: saveName,
        description: `第 ${messages.length} 条消息`,
        snapshot,
      });
      message.success('存档成功');
      setSaveModalVisible(false);
      setSaveName('');
      loadSaves();
    } catch {
      message.error('存档失败');
    }
  };

  const handleLoadSave = (save: Save) => {
    wsService.loadSave(save.id);
  };

  const closeSidebar = () => setSidebarOpen(false);

  // Compute suggestion chips from the last KP message
  const suggestionChips = useMemo(() => {
    // If preset suggestions are available and preset opening is still the latest KP
    if (presetSuggestionsRef.current.length > 0) {
      const hasPresetOpening = messages.some(m => m.id?.startsWith('preset-opening'));
      if (hasPresetOpening) {
        const unused = presetSuggestionsRef.current.filter(s => !usedSuggestions.has(s));
        if (unused.length > 0) return unused;
      }
    }
    // Walk backwards to find the last KP response
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.type === 'kp_response' && m.content) {
        return deriveSuggestions(m.content).filter(s => !usedSuggestions.has(s));
      }
    }
    return [];
  }, [messages, usedSuggestions]);

  // Show suggestions only after the last message is from KP
  const showSuggestions = suggestionChips.length > 0 && messages.length > 0
    && messages[messages.length - 1]?.role === 'kp';

  const renderMessage = (msg: ChatMessage, index: number) => {
    // KP Thinking (collapsible)
    if (msg.type === 'kp_thinking') {
      const thinkingMsg = msg as ThinkingMessage;
      return (
        <div key={msg.id || index} className="message thinking">
          <div
            className="thinking-header"
            onClick={() => msg.id && handleToggleThinking(msg.id)}
            role="button"
            tabIndex={0}
            aria-expanded={!thinkingMsg.collapsed}
            onKeyDown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                if (msg.id) handleToggleThinking(msg.id);
              }
            }}
          >
            <div className="thinking-title">
              {thinkingMsg.collapsed ? (
                <SyncOutlined className="thinking-icon" spin />
              ) : (
                <LoadingOutlined className="thinking-icon" />
              )}
              <span>KP 思考中...</span>
            </div>
            <CaretDownOutlined
              className={`thinking-chevron ${thinkingMsg.collapsed ? '' : 'expanded'}`}
            />
          </div>
          <div
            id={`thinking-content-${msg.id}`}
            className={`thinking-content ${thinkingMsg.collapsed ? 'collapsed' : ''}`}
          >
            {msg.content || '思考中...'}
          </div>
        </div>
      );
    }

    // Dice result
    if (msg.type === 'dice_result') {
      return (
        <div key={index} className="message dice-result">
          <div className="dice-inline-block">
            <div className="dice-big">{msg.total}</div>
            <div className="dice-detail">
              {(msg.rolls && msg.rolls.length > 0) && (
                <div className="dice-rolls">
                  {msg.rolls.map((r, i) => (
                    <span key={i} className="dice-roll-tag">{r}</span>
                  ))}
                  {msg.modifier !== undefined && msg.modifier !== 0 && (
                    <span className="dice-modifier-tag">
                      {msg.modifier > 0 ? '+' : ''}{msg.modifier}
                    </span>
                  )}
                </div>
              )}
              {msg.success !== undefined && (
                <span className={`dice-success ${msg.success ? 'success' : 'failure'}`}>
                  {msg.success ? '成功' : '失败'}
                </span>
              )}
            </div>
          </div>
        </div>
      );
    }

    // System / Error
    if (msg.type === 'system') {
      return (
        <div key={index} className="message system">
          <div className="message-content">{msg.content}</div>
        </div>
      );
    }

    // Player / KP messages
    const isPlayer = msg.role === 'player';
    return (
      <div key={index} className={`message ${msg.role}`}>
        <div className="message-role">
          {isPlayer
            ? selectedCharacter?.name || '玩家'
            : `⚔ GM · ${campaign?.title || '暗幕'}`}
        </div>
        {isPlayer ? (
          <div className="message-content">{msg.content}</div>
        ) : (
          <div className="message-content" dangerouslySetInnerHTML={{ __html: msg.content || '' }} />
        )}
      </div>
    );
  };

  const hpVal = selectedCharacter?.hp ?? 0;

  return (
    <div className="chat-room">
      {/* Mobile overlay */}
      <div
        className="sidebar-overlay"
        style={{
          display: sidebarOpen ? 'block' : 'none',
          position: 'fixed',
          inset: 0,
          background: 'oklch(0% 0 0 / 0.5)',
          zIndex: 299,
        }}
        onClick={closeSidebar}
      />

      {/* Character Sidebar */}
      <aside className={`chat-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-header">
          <h2>角色档案</h2>
          <button className="sidebar-back" onClick={() => navigate('/')}>
            返回大厅
          </button>
        </div>

        <div className="char-panel">
          {selectedCharacter ? (
            <>
              <div className="char-name-block">
                <h3>{selectedCharacter.name}</h3>
                <div className="char-sub">
                  {selectedCharacter.race || '未知种族'} · {selectedCharacter.character_class || '未知职业'} · Lv {selectedCharacter.level}
                </div>
              </div>

              <div className="char-section">
                <div className="char-section-title">生命值</div>
                <div className="hp-bar-label">
                  <span>HP</span>
                  <span>{hpVal}</span>
                </div>
                <div className="hp-bar">
                  <div className="fill" style={{ width: '100%' }} />
                </div>
              </div>

              <div className="char-section">
                <div className="char-section-title">属性</div>
                <div className="stat-mini-grid">
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.STR ?? '—'}</div>
                    <div className="sm-lbl">STR</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.DEX ?? '—'}</div>
                    <div className="sm-lbl">DEX</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.CON ?? '—'}</div>
                    <div className="sm-lbl">CON</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.INT ?? '—'}</div>
                    <div className="sm-lbl">INT</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.WIS ?? '—'}</div>
                    <div className="sm-lbl">WIS</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.attributes?.CHA ?? '—'}</div>
                    <div className="sm-lbl">CHA</div>
                  </div>
                </div>
              </div>

              <div className="char-section">
                <div className="char-section-title">战斗</div>
                <div className="stat-mini-grid">
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.ac || '—'}</div>
                    <div className="sm-lbl">AC</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">Lv {selectedCharacter.level}</div>
                    <div className="sm-lbl">等级</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{hpVal}</div>
                    <div className="sm-lbl">HP</div>
                  </div>
                </div>
              </div>

              <div className="char-section">
                <div className="char-section-title">特质</div>
                <div>
                  <span className="trait-tag">{selectedCharacter.race || '未知'}</span>
                  <span className="trait-tag">{selectedCharacter.character_class || '未知职业'}</span>
                  {selectedCharacter.skills?.map((s, i) => (
                    <span key={i} className="trait-tag">{s}</span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <Empty description="暂无角色" image={Empty.PRESENTED_IMAGE_SIMPLE} />
          )}
        </div>

        {/* Quick Dice */}
        <div className="quick-dice">
          <div className="quick-dice-title">快速掷骰</div>
          <div className="quick-dice-row">
            {QUICK_DICE.map(die => (
              <button
                key={die}
                className={`qd-btn ${die === 'd20' ? 'd20' : ''}`}
                onClick={() => handleQuickRoll(die)}
              >
                {die}
              </button>
            ))}
          </div>
        </div>

        {/* Saves */}
        <div className="save-section">
          <h3>存档列表</h3>
          <List
            size="small"
            dataSource={saves}
            renderItem={(save) => (
              <List.Item
                className="save-item"
                onClick={() => handleLoadSave(save)}
              >
                <List.Item.Meta
                  title={save.name}
                  description={
                    <div className="save-time">
                      {new Date(save.created_at).toLocaleDateString()}
                    </div>
                  }
                />
              </List.Item>
            )}
            locale={{ emptyText: '暂无存档' }}
          />
        </div>
      </aside>

      {/* Chat Area */}
      <div className="chat-area">
        <div className="chat-topbar">
          <button className="menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Menu">
            <MenuOutlined />
          </button>
          <div className="scenario-title">
            {campaign?.title || '加载中...'}
          </div>
          <div className="chat-header-actions">
            <Select
              value={selectedCharacter?.id}
              onChange={(id) =>
                setSelectedCharacter(characters.find((c) => c.id === id) || null)
              }
              placeholder="选择角色"
              style={{ width: 130 }}
              size="small"
            >
              {characters.map((char) => (
                <Select.Option key={char.id} value={char.id}>
                  {char.name}
                </Select.Option>
              ))}
            </Select>
            <button
              className="theme-toggle-btn"
              onClick={toggleTheme}
              title={isDark ? '切换亮色模式' : '切换暗色模式'}
              aria-label="切换主题"
            >
              <BulbOutlined />
            </button>
            <Button
              icon={<SaveOutlined />}
              onClick={() => setSaveModalVisible(true)}
              size="small"
            >
              存档
            </Button>
          </div>
        </div>

        <div
          className="chat-messages"
          role="log"
          aria-live="polite"
          aria-label="聊天消息"
        >
          {messages.length === 0 ? (
            <Empty
              description="开始你的冒险..."
              image={Empty.PRESENTED_IMAGE_SIMPLE}
            />
          ) : (
            messages.map((msg, i) => renderMessage(msg, i))
          )}

          {/* Typing indicator — matches OD GM typing animation */}
          {isKPThinking && messages[messages.length - 1]?.type !== 'kp_thinking' && (
            <div className="message typing-indicator-msg">
              <div className="typing-indicator-content">
                GM 正在编织世界
                <div className="typing-dots">
                  <span />
                  <span />
                  <span />
                </div>
              </div>
            </div>
          )}

          {/* Suggestion chips */}
          {showSuggestions && (
            <div className="suggestions">
              {suggestionChips.map(s => (
                <span
                  key={s}
                  className={`suggestion-chip ${usedSuggestions.has(s) ? 'used' : ''}`}
                  onClick={() => handleSuggestionClick(s)}
                >
                  {s}
                </span>
              ))}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input-area">
          <div className="input-row">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={connected ? '描述你的行动……（Enter 发送，Shift+Enter 换行）' : '连接中...'}
              disabled={!connected}
              className="chat-input"
            />
            <button
              className="send-btn"
              onClick={handleSend}
              disabled={!connected || !inputValue.trim()}
              aria-label="发送"
            >
              <SendOutlined />
            </button>
          </div>
        </div>
      </div>

      {/* Dice Overlay — matching OD dramatic style */}
      {diceOverlay && (
        <div className="dice-overlay show" onClick={() => setDiceOverlay(null)}>
          <div className="dice-overlay-content" onClick={e => e.stopPropagation()}>
            <div className="dice-label-big">{diceOverlay.die.toUpperCase()} 掷骰</div>
            <div className="dice-result-big">{diceOverlay.result}</div>
            <div className="dice-detail" style={{ marginTop: 8, fontSize: 13, color: 'var(--color-text-muted)' }}>
              范围 1—{diceOverlay.max}
            </div>
            <button className="dice-close-btn" onClick={() => setDiceOverlay(null)}>
              关闭
            </button>
          </div>
        </div>
      )}

      {/* Save Modal */}
      <Modal
        title="保存存档"
        open={saveModalVisible}
        onOk={handleSaveGame}
        onCancel={() => setSaveModalVisible(false)}
        okText="保存"
        cancelText="取消"
      >
        <Input
          placeholder="存档名称"
          value={saveName}
          onChange={(e) => setSaveName(e.target.value)}
        />
      </Modal>
    </div>
  );
}
