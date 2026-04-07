import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Input, List, Empty, Modal, Select, message } from 'antd';
import { SendOutlined, RollbackOutlined, SaveOutlined, LoadingOutlined } from '@ant-design/icons';
import { wsService, type ChatMessage } from '../services/websocket';
import { useAuthStore } from '../stores/useAuthStore';
import { campaignAPI, characterAPI, saveAPI } from '../services/api';
import type { Campaign, Character, Save } from '../services/api';
import './ChatRoom.css';

export function ChatRoom() {
  const { campaignId } = useParams<{ campaignId: string }>();
  const navigate = useNavigate();
  const { token } = useAuthStore();
  const [campaign, setCampaign] = useState<Campaign | null>(null);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [selectedCharacter, setSelectedCharacter] = useState<Character | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [connected, setConnected] = useState(false);
  const [saves, setSaves] = useState<Save[]>([]);
  const [saveModalVisible, setSaveModalVisible] = useState(false);
  const [saveName, setSaveName] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<any>(null);

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
  }, [campaignId, token]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const loadCampaign = async () => {
    try {
      const res = await campaignAPI.get(Number(campaignId));
      setCampaign(res.data);
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

  const connectWebSocket = async () => {
    try {
      await wsService.connect(Number(campaignId), token!);

      wsService.onMessage((msg) => {
        if (msg.type === 'history_clear') {
          // 清空消息列表
          setMessages([]);
        } else if (msg.type === 'kp_thinking_chunk') {
          // 更新thinking消息内容
          setMessages((prev) => prev.map((m) =>
            m.id === msg.id ? { ...m, content: (m.content || '') + msg.content } : m
          ));
        } else if (msg.type === 'kp_response') {
          // 替换thinking消息为最终响应
          if (msg.thinking_id) {
            setMessages((prev) => prev.map((m) =>
              m.id === msg.thinking_id ? { ...m, type: 'kp_response', role: 'kp', content: msg.content } : m
            ));
          } else {
            setMessages((prev) => [...prev, msg]);
          }
        } else if (msg.type === 'player_message' || msg.type === 'kp_response' || msg.type === 'dice_result') {
          setMessages((prev) => [...prev, msg]);
        } else if (msg.type === 'kp_thinking') {
          setMessages((prev) => [...prev, { ...msg, role: 'kp', timestamp: new Date().toISOString() }]);
        } else if (msg.type === 'system' || msg.type === 'error') {
          setMessages((prev) => [...prev, { type: 'system', role: 'system', content: msg.content, timestamp: new Date().toISOString() }]);
        } else if (msg.type === 'save_loaded') {
          message.success(msg.content);
        }
      });

      setConnected(true);
    } catch {
      message.error('连接聊天服务器失败');
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = () => {
    if (!inputValue.trim() || !connected) return;
    wsService.sendPlayerMessage(inputValue);
    setInputValue('');
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

  const renderMessage = (msg: ChatMessage, index: number) => {
    if (msg.type === 'kp_thinking') {
      return (
        <div key={msg.id || index} className="message thinking">
          <LoadingOutlined /> {msg.content}
        </div>
      );
    }

    if (msg.type === 'dice_result') {
      return (
        <div key={index} className="message dice-result">
          <div className="dice-result-content">
            <span className="dice-label">投骰结果</span>
            <span className="dice-total">{msg.total}</span>
            <span className="dice-details">
              {msg.rolls?.map((r, i) => (
                <span key={i} className="dice-roll">{r}</span>
              ))}
              {msg.modifier !== undefined && msg.modifier !== 0 && (
                <span className="dice-modifier">
                  {msg.modifier > 0 ? '+' : ''}{msg.modifier}
                </span>
              )}
            </span>
            <span className={`dice-success ${msg.success ? 'success' : 'failure'}`}>
              {msg.success === true ? '✅ 成功' : msg.success === false ? '❌ 失败' : ''}
            </span>
          </div>
        </div>
      );
    }

    if (msg.type === 'system') {
      return (
        <div key={index} className="message system">
          {msg.content}
        </div>
      );
    }

    return (
      <div key={index} className={`message ${msg.role}`}>
        <div className="message-header">
          <span className="message-role">
            {msg.role === 'player' ? (selectedCharacter?.name || '玩家') : 'KP'}
          </span>
        </div>
        <div className="message-content">{msg.content}</div>
      </div>
    );
  };

  return (
    <div className="chat-room">
      <header className="chat-header">
        <Button icon={<RollbackOutlined />} onClick={() => navigate('/')}>
          返回
        </Button>
        <h2>{campaign?.title || '加载中...'}</h2>
        <div className="header-actions">
          <Select
            value={selectedCharacter?.id}
            onChange={(id) => setSelectedCharacter(characters.find((c) => c.id === id) || null)}
            placeholder="选择角色"
            style={{ width: 150 }}
          >
            {characters.map((char) => (
              <Select.Option key={char.id} value={char.id}>
                {char.name}
              </Select.Option>
            ))}
          </Select>
          <Button icon={<SaveOutlined />} onClick={() => setSaveModalVisible(true)}>
            存档
          </Button>
        </div>
      </header>

      <div className="chat-container">
        <aside className="chat-sidebar">
          <h3>快捷投骰</h3>
          <div className="quick-rolls">
            <Button onClick={() => handleQuickRoll('d20')}>D20</Button>
            <Button onClick={() => handleQuickRoll('1d20+5')}>D20+5</Button>
            <Button onClick={() => handleQuickRoll('2d6')}>2D6</Button>
            <Button onClick={() => handleQuickRoll('1d8+3')}>D8+3</Button>
          </div>

          <h3>存档列表</h3>
          <List
            size="small"
            dataSource={saves}
            renderItem={(save) => (
              <List.Item
                className="save-item"
                onClick={() => handleLoadSave(save)}
              >
                <div>
                  <div>{save.name}</div>
                  <div className="save-time">{new Date(save.created_at).toLocaleString()}</div>
                </div>
              </List.Item>
            )}
            locale={{ emptyText: '暂无存档' }}
          />
        </aside>

        <main className="chat-main">
          <div className="messages-container">
            {messages.length === 0 ? (
              <Empty description="开始你的冒险..." image={Empty.PRESENTED_IMAGE_SIMPLE} />
            ) : (
              messages.map((msg, i) => renderMessage(msg, i))
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="chat-input-container">
            <Input
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={connected ? '输入你的行动...' : '连接中...'}
              disabled={!connected}
              className="chat-input"
              suffix={
                <Button
                  type="primary"
                  icon={<SendOutlined />}
                  onClick={handleSend}
                  disabled={!connected || !inputValue.trim()}
                />
              }
            />
          </div>
        </main>
      </div>

      <Modal
        title="保存存档"
        open={saveModalVisible}
        onOk={handleSaveGame}
        onCancel={() => setSaveModalVisible(false)}
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
