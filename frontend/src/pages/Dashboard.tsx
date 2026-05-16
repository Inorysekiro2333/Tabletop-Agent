import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Modal, Form, Input, Select, message, Tag, Popconfirm } from 'antd';
import { PlayCircleOutlined, LogoutOutlined, MenuOutlined, BulbOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/useAuthStore';
import { campaignAPI, characterAPI, aiConfigAPI } from '../services/api';
import type { Campaign, Character, AIConfig } from '../services/api';
import { useTheme } from '../hooks/useTheme';
import { PRESETS, type CampaignPreset } from '../data/presets';
import { CharacterModal } from '../components/CharacterModal';
import './Dashboard.css';

type ViewKey = 'overview' | 'campaigns' | 'characters' | 'ai-configs';

const NAV_ITEMS: { key: ViewKey; icon: string; label: string }[] = [
  { key: 'overview', icon: '✦', label: '总览' },
  { key: 'campaigns', icon: '⚔', label: '战役' },
  { key: 'characters', icon: '♞', label: '角色卡' },
  { key: 'ai-configs', icon: '⚙', label: 'AI 配置' },
];

export function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { isDark, toggle: toggleTheme } = useTheme();
  const [activeView, setActiveView] = useState<ViewKey>('overview');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [aiConfigs, setAiConfigs] = useState<AIConfig[]>([]);
  const [campaignModalVisible, setCampaignModalVisible] = useState(false);
  const [characterModalVisible, setCharacterModalVisible] = useState(false);
  const [editingCharacter, setEditingCharacter] = useState<Character | null>(null);
  const [aiConfigModalVisible, setAiConfigModalVisible] = useState(false);
  const [editingConfigId, setEditingConfigId] = useState<number | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<CampaignPreset | null>(null);
  const [presetStep, setPresetStep] = useState<'select' | 'configure'>('select');
  const [form] = Form.useForm();
  const [aiConfigForm] = Form.useForm();

  const loadData = useCallback(async () => {
    try {
      const [campaignsRes, charactersRes, aiConfigsRes] = await Promise.all([
        campaignAPI.list(),
        characterAPI.list(),
        aiConfigAPI.list(),
      ]);
      setCampaigns(campaignsRes.data);
      setCharacters(charactersRes.data);
      setAiConfigs(aiConfigsRes.data);
    } catch {
      message.error('加载数据失败');
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreateCampaign = async (values: { title: string; description?: string; ai_config_id?: number; character_id?: number }) => {
    try {
      const payload = {
        ...values,
        system_prompt: selectedPreset?.systemPrompt,
      };
      const campaign = await campaignAPI.create(payload);
      setCampaigns(prev => [...prev, campaign.data]);
      closeCampaignModal();
      message.success('战役创建成功');
    } catch {
      message.error('创建失败');
    }
  };

  const handleCharacterSuccess = () => {
    loadData();
  };

  const handleOpenCreateCharacter = () => {
    setEditingCharacter(null);
    setCharacterModalVisible(true);
  };

  const handleEditCharacter = (character: Character) => {
    setEditingCharacter(character);
    setCharacterModalVisible(true);
  };

  const handleDeleteCharacter = async (id: number) => {
    try {
      await characterAPI.delete(id);
      setCharacters(prev => prev.filter(c => c.id !== id));
      message.success('角色已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleSaveAIConfig = async (values: { provider: string; api_key: string; base_url?: string; model_name: string }) => {
    try {
      if (editingConfigId) {
        const payload: Record<string, string> = {};
        payload.provider = values.provider;
        payload.model_name = values.model_name;
        if (values.api_key) payload.api_key = values.api_key;
        if (values.base_url) payload.base_url = values.base_url;
        const res = await aiConfigAPI.update(editingConfigId, payload);
        setAiConfigs(prev => prev.map(c => c.id === editingConfigId ? res.data : c));
        message.success('AI 配置更新成功');
      } else {
        const res = await aiConfigAPI.create(values);
        setAiConfigs(prev => [...prev, res.data]);
        message.success('AI 配置创建成功');
      }
      closeAiConfigModal();
    } catch {
      message.error(editingConfigId ? '更新失败' : '创建失败');
    }
  };

  const handleEditAIConfig = (config: AIConfig) => {
    setEditingConfigId(config.id);
    aiConfigForm.setFieldsValue({
      provider: config.provider,
      api_key: '',
      base_url: config.base_url || '',
      model_name: config.model_name,
    });
    setAiConfigModalVisible(true);
  };

  const handleDeleteAIConfig = async (id: number) => {
    try {
      await aiConfigAPI.delete(id);
      setAiConfigs(prev => prev.filter(c => c.id !== id));
      message.success('AI 配置已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleActivateAIConfig = async (id: number) => {
    try {
      await aiConfigAPI.activate(id);
      setAiConfigs(prev => prev.map(c => ({ ...c, is_active: c.id === id })));
      message.success('AI 配置已激活');
    } catch {
      message.error('激活失败');
    }
  };

  const handlePlay = (campaignId: number) => {
    navigate(`/chat/${campaignId}`);
  };

  const handleDeleteCampaign = async (id: number) => {
    try {
      await campaignAPI.delete(id);
      setCampaigns(prev => prev.filter(c => c.id !== id));
      message.success('战役已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const handleSelectPreset = (preset: CampaignPreset | null) => {
    setSelectedPreset(preset);
    if (preset) {
      form.setFieldsValue({
        title: preset.title,
        description: preset.description,
      });
    } else {
      form.resetFields();
    }
    setPresetStep('configure');
  };

  const closeCampaignModal = () => {
    setCampaignModalVisible(false);
    setSelectedPreset(null);
    setPresetStep('select');
    form.resetFields();
  };

  const openCampaignModal = () => {
    setPresetStep('select');
    setSelectedPreset(null);
    form.resetFields();
    setCampaignModalVisible(true);
  };

  const openAiConfigModal = () => {
    setEditingConfigId(null);
    aiConfigForm.resetFields();
    setAiConfigModalVisible(true);
  };

  const closeAiConfigModal = () => {
    setAiConfigModalVisible(false);
    setEditingConfigId(null);
    aiConfigForm.resetFields();
  };

  const activeCampaigns = campaigns.filter(c => c.status === 'active').length;
  const archivedCampaigns = campaigns.filter(c => c.status !== 'active').length;
  const activeAiConfig = aiConfigs.find(c => c.is_active);

  const handleNavClick = (key: ViewKey) => {
    setActiveView(key);
    setSidebarOpen(false);
  };

  const overviewContent = (
    <div>
      <div className="eyebrow">大厅</div>
      <h1>暗<span style={{ color: 'var(--color-accent-primary)' }}>幕</span></h1>
      <p style={{ color: 'var(--color-text-secondary)', fontSize: 14, maxWidth: 560 }}>
        欢迎回来，{user?.username}。你的冒险正在等待。
      </p>
      <div className="overview-grid">
        <div className="dashboard-card">
          <h3>冒险统计</h3>
          <div className="stat-row">
            <div className="stat-item">
              <div className="stat-val">{activeCampaigns}</div>
              <div className="stat-lbl">进行中</div>
            </div>
            <div className="stat-item">
              <div className="stat-val">{characters.length}</div>
              <div className="stat-lbl">角色卡</div>
            </div>
            <div className="stat-item">
              <div className="stat-val">{archivedCampaigns}</div>
              <div className="stat-lbl">已归档</div>
            </div>
          </div>
        </div>
        <div className="dashboard-card">
          <h3>快捷操作</h3>
          <div className="quick-actions">
            <Button type="primary" onClick={openCampaignModal}>
              创建战役
            </Button>
            <Button onClick={() => { setActiveView('characters'); handleOpenCreateCharacter(); }}>
              创建角色卡
            </Button>
            <Button onClick={() => { setActiveView('ai-configs'); setAiConfigModalVisible(true); }}>
              AI 配置
            </Button>
          </div>
        </div>
        {activeAiConfig && (
          <div className="dashboard-card">
            <h3>当前 AI</h3>
            <div className="stat-row">
              <div className="stat-item">
                <div className="stat-val" style={{ fontSize: 24 }}>{activeAiConfig.provider.toUpperCase()}</div>
                <div className="stat-lbl">提供商</div>
              </div>
              <div className="stat-item">
                <div className="stat-val" style={{ fontSize: 24 }}>{activeAiConfig.model_name}</div>
                <div className="stat-lbl">模型</div>
              </div>
            </div>
          </div>
        )}
        {activeCampaigns > 0 && (
          <div className="dashboard-card card-full">
            <h3>进行中的战役</h3>
            <div className="active-campaign-list">
              {campaigns.filter(c => c.status === 'active').map(campaign => (
                <div key={campaign.id} className="active-campaign-item">
                  <div className="active-campaign-info">
                    <div className="active-campaign-title">{campaign.title}</div>
                    <div className="active-campaign-desc">
                      {campaign.description || '暂无描述'} · 第 {campaign.current_session} 节
                    </div>
                    <div className="active-campaign-meta">
                      创建于 {new Date(campaign.created_at).toLocaleDateString()}
                      {campaign.last_played_at && ` · 上次游玩 ${new Date(campaign.last_played_at).toLocaleDateString()}`}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
                    <Button
                      type="primary"
                      icon={<PlayCircleOutlined />}
                      onClick={() => handlePlay(campaign.id)}
                    >
                      继续冒险
                    </Button>
                    <Popconfirm
                      title="确定删除此战役？"
                      description="删除后无法恢复"
                      onConfirm={() => handleDeleteCampaign(campaign.id)}
                      okText="删除"
                      cancelText="取消"
                    >
                      <Button danger icon={<DeleteOutlined />} />
                    </Popconfirm>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const campaignsContent = (
    <div>
      <div className="eyebrow">战役管理</div>
      <h1>战役</h1>
      <div className="card-grid">
        <div className="add-card" onClick={openCampaignModal}>
          <div className="add-icon">+</div>
          <span>创建战役</span>
        </div>
        {campaigns.map(campaign => (
          <Card
            key={campaign.id}
            title={campaign.title}
            className="campaign-card"
            extra={
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handlePlay(campaign.id)}
                >
                  开始
                </Button>
                <Popconfirm
                  title="确定删除此战役？"
                  description="删除后无法恢复"
                  onConfirm={() => handleDeleteCampaign(campaign.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            }
          >
            <p>{campaign.description || '暂无描述'}</p>
            <p style={{ fontSize: 11, color: 'var(--color-text-muted)', marginTop: 8 }}>
              创建于 {new Date(campaign.created_at).toLocaleDateString()}
              {campaign.last_played_at && ` · 最近游玩 ${new Date(campaign.last_played_at).toLocaleDateString()}`}
            </p>
            <Tag color={campaign.status === 'active' ? 'green' : 'default'}>
              {campaign.status === 'active' ? '进行中' : '已归档'}
            </Tag>
          </Card>
        ))}
      </div>
    </div>
  );

  const charactersContent = (
    <div>
      <div className="eyebrow">角色管理</div>
      <h1>角色卡</h1>
      <div className="card-grid">
        <div className="add-card" onClick={handleOpenCreateCharacter}>
          <div className="add-icon">+</div>
          <span>创建角色卡</span>
        </div>
        {characters.map(character => (
          <Card
            key={character.id}
            title={character.name}
            extra={
              <div style={{ display: 'flex', gap: 4 }}>
                <Button size="small" onClick={() => handleEditCharacter(character)}>编辑</Button>
                <Popconfirm
                  title="确定删除此角色？"
                  description="删除后无法恢复，关联的战役将失去角色绑定"
                  onConfirm={() => handleDeleteCharacter(character.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button size="small" danger>删除</Button>
                </Popconfirm>
              </div>
            }
          >
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 12px', fontSize: 13 }}>
              <div><span style={{ color: 'var(--color-text-muted)' }}>种族</span> {character.race || '未知'}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>职业</span> {character.character_class || '未知'}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>等级</span> Lv.{character.level}</div>
              <div><span style={{ color: 'var(--color-text-muted)' }}>HP</span> {character.hp} / AC {character.ac}</div>
              {character.faction && <div style={{ gridColumn: '1 / -1' }}><span style={{ color: 'var(--color-text-muted)' }}>阵营</span> {character.faction}</div>}
            </div>
            {character.backstory && (
              <p style={{ fontSize: 12, color: 'var(--color-text-secondary)', margin: '8px 0 0', lineHeight: 1.5, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {character.backstory}
              </p>
            )}
          </Card>
        ))}
      </div>
    </div>
  );

  const aiConfigsContent = (
    <div>
      <div className="eyebrow">AI 设置</div>
      <h1>AI 配置</h1>
      <div className="card-grid">
        <div className="add-card" onClick={openAiConfigModal}>
          <div className="add-icon">+</div>
          <span>添加 AI 配置</span>
        </div>
        {aiConfigs.map(config => (
          <Card
            key={config.id}
            title={config.provider.toUpperCase()}
            extra={
              <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                {config.is_active && <Tag color="gold">使用中</Tag>}
                <Button
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEditAIConfig(config)}
                />
                <Popconfirm
                  title="确定删除此配置？"
                  onConfirm={() => handleDeleteAIConfig(config.id)}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button size="small" danger icon={<DeleteOutlined />} />
                </Popconfirm>
              </div>
            }
          >
            <p>模型: {config.model_name}</p>
            <p>API Key: {config.api_key_masked}</p>
            {config.base_url && <p>端点: {config.base_url}</p>}
            <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
              {!config.is_active && (
                <Button
                  size="small"
                  type="primary"
                  onClick={() => handleActivateAIConfig(config.id)}
                >
                  激活
                </Button>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  );

  const viewContent: Record<ViewKey, React.ReactNode> = {
    overview: overviewContent,
    campaigns: campaignsContent,
    characters: charactersContent,
    'ai-configs': aiConfigsContent,
  };

  return (
    <div className="dashboard">
      <button className="menu-btn" onClick={() => setSidebarOpen(true)} aria-label="Menu">
        <MenuOutlined />
      </button>
      <div className={`sidebar-overlay ${sidebarOpen ? 'on' : ''}`} onClick={() => setSidebarOpen(false)} />

      <aside className={`dashboard-sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-brand">暗<span>幕</span></div>
        <ul className="sidebar-nav">
          {NAV_ITEMS.map(item => (
            <li key={item.key}>
              <button
                className={`sidebar-nav-btn ${activeView === item.key ? 'active' : ''}`}
                onClick={() => handleNavClick(item.key)}
              >
                <span className="nav-icon">{item.icon}</span>
                {item.label}
              </button>
            </li>
          ))}
        </ul>
        <div className="sidebar-footer">
          <button className="theme-toggle" onClick={toggleTheme}>
            <BulbOutlined /> {isDark ? '亮色模式' : '暗色模式'}
          </button>
          <button className="sidebar-logout" onClick={logout}>
            <LogoutOutlined /> 退出登录
          </button>
        </div>
      </aside>

      <main className="dashboard-main">
        {Object.entries(viewContent).map(([key, content]) => (
          <div key={key} className={`dashboard-view ${activeView === key ? 'active' : ''}`}>
            {content}
          </div>
        ))}
      </main>

      {/* Campaign Modal — two-step: preset selection → configure */}
      <Modal
        title={presetStep === 'select' ? '选择剧本预设' : '创建战役'}
        open={campaignModalVisible}
        onCancel={closeCampaignModal}
        footer={null}
        width={presetStep === 'select' ? 720 : 520}
      >
        {presetStep === 'select' ? (
          <div className="preset-grid">
            {PRESETS.map(preset => (
              <div
                key={preset.key}
                className="preset-card"
                onClick={() => handleSelectPreset(preset)}
              >
                <div className="preset-card-accent" />
                <div className="preset-icon">{preset.icon}</div>
                <h3>{preset.title}</h3>
                <p className="preset-desc">{preset.description}</p>
                <div className="preset-tags">
                  {preset.tags.map(tag => (
                    <span key={tag} className="preset-tag">{tag}</span>
                  ))}
                </div>
              </div>
            ))}
            <div
              className="preset-card custom-card"
              onClick={() => handleSelectPreset(null)}
            >
              <div className="preset-icon" style={{ fontSize: 48, fontFamily: 'var(--font-display)', opacity: 0.5 }}>+</div>
              <h3>创建自定义剧本</h3>
              <p className="preset-desc">自由设定世界观、规则系统和角色，一切由你掌控。</p>
            </div>
          </div>
        ) : (
          <div>
            {selectedPreset && (
              <div className="selected-preset-info">
                <span className="preset-badge">{selectedPreset.icon} {selectedPreset.title}</span>
                <Button type="link" size="small" onClick={() => setPresetStep('select')}>
                  更换预设
                </Button>
              </div>
            )}
            <Form form={form} onFinish={handleCreateCampaign} layout="vertical">
              <Form.Item name="title" label="战役名称" rules={[{ required: true }]}>
                <Input placeholder="例如：失落的矿山" />
              </Form.Item>
              <Form.Item name="description" label="描述">
                <Input.TextArea placeholder="描述你的战役..." rows={2} />
              </Form.Item>
              <Form.Item name="character_id" label="游玩角色">
                <Select placeholder="选择游玩角色" allowClear>
                  {characters.map(char => (
                    <Select.Option key={char.id} value={char.id}>
                      {char.name} — {char.character_class || '未知职业'} Lv.{char.level}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Form.Item name="ai_config_id" label="AI 配置">
                <Select placeholder="选择 AI 配置" allowClear>
                  {aiConfigs.map(config => (
                    <Select.Option key={config.id} value={config.id}>
                      {config.provider.toUpperCase()} - {config.model_name}
                    </Select.Option>
                  ))}
                </Select>
              </Form.Item>
              <Button type="primary" htmlType="submit" block>
                创建战役
              </Button>
            </Form>
          </div>
        )}
      </Modal>

      {/* Character Modal */}
      <CharacterModal
        visible={characterModalVisible}
        character={editingCharacter}
        onClose={() => { setCharacterModalVisible(false); setEditingCharacter(null); }}
        onSuccess={handleCharacterSuccess}
      />

      {/* AI Config Modal */}
      <Modal
        title={editingConfigId ? '编辑 AI 配置' : '添加 AI 配置'}
        open={aiConfigModalVisible}
        onCancel={closeAiConfigModal}
        footer={null}
      >
        <Form form={aiConfigForm} onFinish={handleSaveAIConfig} layout="vertical">
          <Form.Item name="provider" label="提供商" rules={[{ required: true }]}>
            <Select placeholder="选择 AI 提供商">
              <Select.Option value="deepseek">DeepSeek</Select.Option>
              <Select.Option value="claude">Claude</Select.Option>
              <Select.Option value="minimax">MiniMax</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item
            name="api_key"
            label="API Key"
            rules={editingConfigId ? [] : [{ required: true, message: '请输入 API Key' }]}
            extra={editingConfigId ? '留空则不修改现有 Key' : undefined}
          >
            <Input.Password placeholder={editingConfigId ? '留空保留原 Key...' : '输入 API Key'} />
          </Form.Item>
          <Form.Item name="base_url" label="自定义端点 (可选)">
            <Input placeholder="例如: https://api.deepseek.com" />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true, message: '请输入模型名称' }]}>
            <Input placeholder="例如: deepseek-chat" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            {editingConfigId ? '更新配置' : '保存'}
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
