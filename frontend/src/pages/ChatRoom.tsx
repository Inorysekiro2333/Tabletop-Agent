import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Input, List, Empty, Modal, Select, message } from 'antd';
import type { InputRef } from 'antd';
import {
  SendOutlined,
  SaveOutlined,
  MenuOutlined,
  BulbOutlined,
  BranchesOutlined,
  CloseOutlined,
  RightOutlined,
  LeftOutlined,
} from '@ant-design/icons';
import { wsService, type ChatMessage } from '../services/websocket';
import { useAuthStore } from '../stores/useAuthStore';
import { campaignAPI, characterAPI, saveAPI } from '../services/api';
import type { Campaign, Character, Save } from '../services/api';
import { useTheme } from '../hooks/useTheme';
import { PRESETS } from '../data/presets';
import './ChatRoom.css';

const QUICK_DICE = ['d4', 'd6', 'd8', 'd10', 'd12', 'd20', 'd100'];

/** Parse formatted AI response into styled segments */
interface FormattedSegment {
  type: 'desc' | 'action' | 'npc' | 'event' | 'status' | 'text';
  content: string;
}

function parseFormattedContent(content: string): FormattedSegment[] {
  const segments: FormattedSegment[] = [];
  const markerRegex = /\[(DESC|ACTION|NPC|EVENT|STATUS)\]([\s\S]*?)\[\/\1\]/g;
  let lastIndex = 0;

  const matches: Array<{ index: number; length: number; type: string; content: string }> = [];
  let match;
  while ((match = markerRegex.exec(content)) !== null) {
    matches.push({ index: match.index, length: match[0].length, type: match[1].toLowerCase(), content: match[2].trim() });
  }

  if (matches.length === 0) {
    return [{ type: 'text', content }];
  }

  for (const m of matches) {
    if (m.index > lastIndex) {
      const before = content.slice(lastIndex, m.index).trim();
      if (before) segments.push({ type: 'text', content: before });
    }
    segments.push({ type: m.type as FormattedSegment['type'], content: m.content });
    lastIndex = m.index + m.length;
  }

  if (lastIndex < content.length) {
    const after = content.slice(lastIndex).trim();
    if (after) segments.push({ type: 'text', content: after });
  }

  return segments;
}

export function ChatRoom() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const { isDark, toggle: toggleTheme } = useTheme();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [connected, setConnected] = useState(false);
  const [saves, setSaves] = useState<Save[]>([]);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveName, setSaveName] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [diceOverlay, setDiceOverlay] = useState<{ die: string; result: number; max: number } | null>(null);
  const [usedSuggestions, setUsedSuggestions] = useState<Set<string>>(new Set());
  const [isKPThinking, setIsKPThinking] = useState(false);
  // 分支侧边栏
  const [branchPanelOpen, setBranchPanelOpen] = useState(false);
  const [branchPanelCollapsed, setBranchPanelCollapsed] = useState(false);
  const [branchMessages, setBranchMessages] = useState<ChatMessage[]>([]);
  const [branchInputValue, setBranchInputValue] = useState('');
  const [branchCreated, setBranchCreated] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const branchMessagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<InputRef>(null);
  const branchInputRef = useRef<InputRef>(null);
  const skipBackendInitRef = useRef(true);
  const usePresetRef = useRef(false);
  const presetSuggestionsRef = useRef<string[]>([]);

  const loadCampaign = async () => {
    try {
      const res = await campaignAPI.get(Number(campaignId));
      setCampaign(res.data);

      const preset = PRESETS.find(p => p.systemPrompt === res.data.system_prompt);
      if (preset) {
        usePresetRef.current = true;
        const now = new Date().toISOString();
        const openingMsgs: ChatMessage[] = preset.opening.map((o, i) => ({
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
    if (skipBackendInitRef.current) {
      if (msg.type === 'system' || msg.type === 'kp_thinking' || msg.type === 'kp_thinking_chunk') {
        return;
      }
      if (msg.type === 'kp_response') {
        skipBackendInitRef.current = false;
        setIsKPThinking(false);
        if (usePresetRef.current) return;
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
      presetSuggestionsRef.current = [];
      if (msg.thinking_id) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === msg.thinking_id
              ? { ...m, type: 'kp_response', role: 'kp', content: msg.content, suggestions: msg.suggestions }
              : m
          )
        );
      } else {
        setMessages((prev) => [...prev, msg]);
      }
      setUsedSuggestions(new Set());
    } else if (msg.type === 'player_message' || msg.type === 'dice_result') {
      setMessages((prev) => [...prev, msg]);
    } else if (msg.type === 'kp_thinking') {
      setIsKPThinking(true);
      setMessages((prev) => [
        ...prev,
        { ...msg, type: 'kp_response', role: 'kp', content: '', timestamp: new Date().toISOString() },
      ]);
    } else if (msg.type === 'character_update') {
      setIsKPThinking(false);
      if (msg.stats) {
        setSelectedCharacter((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            hp: msg.stats!.hp ?? prev.hp,
            ac: msg.stats!.ac ?? prev.ac,
            level: msg.stats!.level ?? prev.level,
            attributes: {
              STR: msg.stats!.STR ?? prev.attributes?.STR ?? 10,
              DEX: msg.stats!.DEX ?? prev.attributes?.DEX ?? 10,
              CON: msg.stats!.CON ?? prev.attributes?.CON ?? 10,
              INT: msg.stats!.INT ?? prev.attributes?.INT ?? 10,
              WIS: msg.stats!.WIS ?? prev.attributes?.WIS ?? 10,
              CHA: msg.stats!.CHA ?? prev.attributes?.CHA ?? 10,
            },
          };
        });
      }
      if (msg.updates) {
        const changes = Object.entries(msg.updates)
          .map(([k, v]) => `${k}${v > 0 ? '+' : ''}${v}`)
          .join('，');
        setMessages((prev) => [
          ...prev,
          {
            type: 'system',
            role: 'system',
            content: `角色状态变化: ${changes}`,
            timestamp: new Date().toISOString(),
          },
        ]);
      }
    } else if (msg.type === 'system' || msg.type === 'error') {
      setMessages((prev) => [
        ...prev,
        { type: 'system', role: 'system', content: msg.content, timestamp: new Date().toISOString() },
      ]);
    } else if (msg.type === 'save_loaded') {
      message.success(msg.content);
      if (msg.character_stats) {
        setSelectedCharacter((prev) => {
          if (!prev) return prev;
          return {
            ...prev,
            hp: msg.character_stats!.hp ?? prev.hp,
            ac: msg.character_stats!.ac ?? prev.ac,
            level: msg.character_stats!.level ?? prev.level,
            attributes: {
              STR: msg.character_stats!.STR ?? prev.attributes?.STR ?? 10,
              DEX: msg.character_stats!.DEX ?? prev.attributes?.DEX ?? 10,
              CON: msg.character_stats!.CON ?? prev.attributes?.CON ?? 10,
              INT: msg.character_stats!.INT ?? prev.attributes?.INT ?? 10,
              WIS: msg.character_stats!.WIS ?? prev.attributes?.WIS ?? 10,
              CHA: msg.character_stats!.CHA ?? prev.attributes?.CHA ?? 10,
            },
          };
        });
      }
      if (msg.selected_character) {
        const sc = msg.selected_character as Record<string, unknown>;
        setSelectedCharacter((prev) => ({
          ...prev,
          ...sc,
          id: (sc.id as number) ?? prev?.id ?? 0,
          name: (sc.name as string) ?? prev?.name ?? '',
        }) as Character);
      }
      loadSaves();
    } else if (msg.type === 'save_created') {
      message.success(msg.content);
      loadSaves();
    }
    // 分支消息 — 路由到分支面板
    else if (msg.type === 'branch_created') {
      setBranchCreated(true);
      setBranchPanelOpen(true);
      setBranchPanelCollapsed(false);
      message.success('分支对话已创建，在右侧面板聊天');
    } else if (msg.type === 'branch_kp_thinking') {
      setBranchMessages((prev) => [
        ...prev,
        { ...msg, type: 'kp_response' as const, role: 'kp', content: '', timestamp: new Date().toISOString() },
      ]);
    } else if (msg.type === 'branch_kp_thinking_chunk') {
      setBranchMessages((prev) =>
        prev.map((m) =>
          m.id === msg.id ? { ...m, content: (m.content || '') + msg.content } : m
        )
      );
    } else if (msg.type === 'branch_kp_response') {
      if (msg.thinking_id) {
        setBranchMessages((prev) =>
          prev.map((m) =>
            m.id === msg.thinking_id
              ? { ...m, type: 'kp_response', role: 'kp', content: msg.content }
              : m
          )
        );
      } else {
        setBranchMessages((prev) => [...prev, msg]);
      }
    } else if (msg.type === 'branch_player_message') {
      setBranchMessages((prev) => [...prev, msg]);
    } else if (msg.type === 'branch_system') {
      setBranchMessages((prev) => [...prev, { ...msg, type: 'system', role: 'system' }]);
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

  useEffect(() => {
    branchMessagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [branchMessages]);

  const handleSend = () => {
    if (!inputValue.trim() || !connected) return;
    wsService.sendPlayerMessage(inputValue);
    setInputValue('');
    setIsKPThinking(true);
    inputRef.current?.focus();
  };

  const handleSuggestionClick = (suggestion: string) => {
    setInputValue(suggestion);
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

  const handleSaveGame = () => {
    if (!saveName.trim()) {
      message.warning('请输入存档名称');
      return;
    }
    if (!connected) {
      message.error('未连接到聊天服务器');
      return;
    }
    wsService.sendSaveGame(saveName);
    message.success('存档请求已发送');
    setSaveModalVisible(false);
    setSaveName('');
  };

  const handleLoadSave = (save: Save) => {
    wsService.loadSave(save.id);
  };

  const closeSidebar = () => setSidebarOpen(false);

  // ── 分支操作 ──
  const handleForkFromMessage = (msgIndex: number) => {
    if (!connected) return;
    wsService.createBranch(`分支 ${new Date().toLocaleTimeString()}`);
  };

  const handleBranchSend = () => {
    if (!branchInputValue.trim() || !connected) return;
    wsService.sendBranchMessage(branchInputValue);
    // Optimistic add
    setBranchMessages((prev) => [
      ...prev,
      { type: 'player_message', role: 'player', content: branchInputValue, timestamp: new Date().toISOString() },
    ]);
    setBranchInputValue('');
    branchInputRef.current?.focus();
  };

  const handleBranchKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleBranchSend();
    }
  };

  const handleToggleBranchPanel = () => {
    if (branchPanelCollapsed) {
      setBranchPanelCollapsed(false);
      setBranchPanelOpen(true);
    } else {
      setBranchPanelCollapsed(true);
    }
  };

  const handleCloseBranch = () => {
    setBranchPanelOpen(false);
    setBranchPanelCollapsed(false);
    setBranchMessages([]);
    setBranchCreated(false);
  };

  // Compute suggestion chips from the last KP message (AI-generated)
  const suggestionChips = useMemo(() => {
    if (presetSuggestionsRef.current.length > 0) {
      const hasPresetOpening = messages.some(m => m.id?.startsWith('preset-opening'));
      if (hasPresetOpening) {
        return presetSuggestionsRef.current;
      }
    }
    // Use AI-generated suggestions from the last KP message
    for (let i = messages.length - 1; i >= 0; i--) {
      const m = messages[i];
      if (m.type === 'kp_response' && m.suggestions && m.suggestions.length > 0) {
        return m.suggestions;
      }
    }
    return [];
  }, [messages]);

  const showSuggestions = !isKPThinking && suggestionChips.length > 0 && messages.length > 0
    && messages[messages.length - 1]?.role === 'kp';

  const renderFormattedContent = (content: string, isStreaming: boolean) => {
    const segments = parseFormattedContent(content);
    return (
      <>
        {segments.map((seg, i) => {
          if (seg.type === 'text') {
            return <span key={i} dangerouslySetInnerHTML={{ __html: seg.content }} />;
          }
          return (
            <span key={i} className={`fm-seg fm-${seg.type}`}>
              <span className="fm-seg-content" dangerouslySetInnerHTML={{ __html: seg.content }} />
            </span>
          );
        })}
        {isStreaming && <span className="streaming-cursor" />}
      </>
    );
  };

  const renderMessage = (msg: ChatMessage, index: number) => {
    const isLastKpMessage = msg.role === 'kp' && isKPThinking && index === messages.length - 1;

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

    if (msg.type === 'system') {
      return (
        <div key={index} className="message system">
          <div className="message-content">{msg.content}</div>
        </div>
      );
    }

    const isPlayer = msg.role === 'player';
    const isKP = msg.role === 'kp';

    return (
      <div key={index} className={`message ${msg.role}`}>
        <div className="message-role">
          {isPlayer
            ? selectedCharacter?.name || '玩家'
            : `⚔ KP · ${campaign?.title || '暗幕'}`}
        </div>
        {isPlayer ? (
          <div className="message-content">{msg.content}</div>
        ) : (
          <div className={`message-content${isLastKpMessage ? ' streaming' : ''}`}>
            {renderFormattedContent(msg.content || '', isLastKpMessage)}
            {/* Fork button INSIDE message-content so hover works */}
            {isKP && msg.content && !isLastKpMessage && (
              <button
                className="fork-btn"
                onClick={(e) => { e.stopPropagation(); handleForkFromMessage(index); }}
                title="从当前创建分支对话"
              >
                <BranchesOutlined /> 从当前创建分支
              </button>
            )}
          </div>
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
                  {(['STR','DEX','CON','INT','WIS','CHA'] as const).map(attr => {
                    const labels: Record<string, string> = {STR:'力量',DEX:'敏捷',CON:'体质',INT:'智力',WIS:'感知',CHA:'魅力'};
                    return (
                      <div key={attr} className="stat-mini">
                        <div className="sm-val">{selectedCharacter.attributes?.[attr] ?? '—'}</div>
                        <div className="sm-lbl">{labels[attr]}</div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="char-section">
                <div className="char-section-title">战斗</div>
                <div className="stat-mini-grid">
                  <div className="stat-mini">
                    <div className="sm-val">{selectedCharacter.ac || '—'}</div>
                    <div className="sm-lbl">护甲</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">Lv {selectedCharacter.level}</div>
                    <div className="sm-lbl">等级</div>
                  </div>
                  <div className="stat-mini">
                    <div className="sm-val">{hpVal}</div>
                    <div className="sm-lbl">生命</div>
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

              <div className="char-section">
                <div className="char-section-title">背包</div>
                {selectedCharacter.equipment && selectedCharacter.equipment.length > 0 ? (
                  <ul className="inventory-list">
                    {selectedCharacter.equipment.map((item, i) => (
                      <li key={i} className="inventory-item">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <div className="inventory-empty">空背包</div>
                )}
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
              onChange={(id) => {
                const char = characters.find((c) => c.id === id) || null;
                setSelectedCharacter(char);
                if (id) {
                  wsService.selectCharacter(id);
                }
              }}
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

          {/* AI-generated suggestion chips */}
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

      {/* ── 分支聊天侧边面板 (右) ── */}
      {branchPanelOpen && (
        <div className={`branch-panel ${branchPanelCollapsed ? 'collapsed' : ''}`}>
          {branchPanelCollapsed ? (
            // Collapsed state — thin bar at right edge
            <div className="branch-collapsed-bar" onClick={handleToggleBranchPanel}>
              <LeftOutlined className="branch-toggle-icon" />
              <span className="branch-collapsed-label">分支对话</span>
            </div>
          ) : (
            // Expanded state
            <>
              <div className="branch-panel-header">
                <div className="branch-panel-title">
                  <BranchesOutlined /> 分支对话
                </div>
                <div className="branch-panel-actions">
                  <button
                    className="branch-collapse-btn"
                    onClick={handleToggleBranchPanel}
                    title="折叠分支面板"
                  >
                    <RightOutlined />
                  </button>
                  <button
                    className="branch-close-btn"
                    onClick={handleCloseBranch}
                    title="关闭分支"
                  >
                    <CloseOutlined />
                  </button>
                </div>
              </div>

              <div className="branch-panel-messages">
                {branchMessages.length === 0 ? (
                  <Empty
                    description="在分支中与 AI 对话，不会影响主线剧情"
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                  />
                ) : (
                  branchMessages.map((msg, i) => {
                    const isLastBranchKp = msg.role === 'kp' && i === branchMessages.length - 1 && !msg.content;
                    return (
                    <div key={i} className={`branch-msg ${msg.role}`}>
                      <div className="branch-msg-role">
                        {msg.role === 'player'
                          ? selectedCharacter?.name || '玩家'
                          : '💬 闲聊'}
                      </div>
                      <div className="branch-msg-content">
                        {msg.role === 'kp' ? (
                          <span>
                            <span dangerouslySetInnerHTML={{ __html: msg.content || '' }} />
                            {isLastBranchKp && <span className="streaming-cursor" />}
                          </span>
                        ) : (
                          msg.content
                        )}
                      </div>
                    </div>
                    );
                  })
                )}
                <div ref={branchMessagesEndRef} />
              </div>

              <div className="branch-panel-input">
                <div className="input-row">
                  <Input
                    ref={branchInputRef}
                    value={branchInputValue}
                    onChange={(e) => setBranchInputValue(e.target.value)}
                    onKeyPress={handleBranchKeyPress}
                    placeholder="在分支中闲聊……（不影响主线）"
                    disabled={!connected}
                    className="chat-input"
                  />
                  <button
                    className="send-btn branch-send"
                    onClick={handleBranchSend}
                    disabled={!connected || !branchInputValue.trim()}
                    aria-label="发送分支消息"
                  >
                    <SendOutlined />
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* Dice Overlay */}
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
