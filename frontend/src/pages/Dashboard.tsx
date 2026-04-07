import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Button, Modal, Form, Input, Select, message, Tabs, Tag } from 'antd';
import { PlusOutlined, PlayCircleOutlined, SettingOutlined } from '@ant-design/icons';
import { useAuthStore } from '../stores/useAuthStore';
import { campaignAPI, characterAPI, aiConfigAPI } from '../services/api';
import type { Campaign, Character, AIConfig } from '../services/api';
import './Dashboard.css';

export function Dashboard() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [characters, setCharacters] = useState<Character[]>([]);
  const [aiConfigs, setAiConfigs] = useState<AIConfig[]>([]);
  const [campaignModalVisible, setCampaignModalVisible] = useState(false);
  const [characterModalVisible, setCharacterModalVisible] = useState(false);
  const [aiConfigModalVisible, setAiConfigModalVisible] = useState(false);
  const [form] = Form.useForm();
  const [characterForm] = Form.useForm();
  const [aiConfigForm] = Form.useForm();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [campaignsRes, charactersRes, aiConfigsRes] = await Promise.all([
        campaignAPI.list(),
        characterAPI.list(),
        aiConfigAPI.list(),
      ]);
      setCampaigns(campaignsRes.data);
      setCharacters(charactersRes.data);
      setAiConfigs(aiConfigsRes.data);
    } catch (error) {
      message.error('加载数据失败');
    }
  };

  const handleCreateCampaign = async (values: { title: string; description?: string; ai_config_id?: number }) => {
    try {
      const campaign = await campaignAPI.create(values);
      setCampaigns([...campaigns, campaign.data]);
      setCampaignModalVisible(false);
      form.resetFields();
      message.success('战役创建成功');
    } catch {
      message.error('创建失败');
    }
  };

  const handleCreateCharacter = async (values: Partial<Character>) => {
    try {
      const character = await characterAPI.create(values);
      setCharacters([...characters, character.data]);
      setCharacterModalVisible(false);
      characterForm.resetFields();
      message.success('角色卡创建成功');
    } catch {
      message.error('创建失败');
    }
  };

  const handleCreateAIConfig = async (values: { provider: string; api_key: string; base_url?: string; model_name: string }) => {
    try {
      const config = await aiConfigAPI.create(values);
      setAiConfigs([...aiConfigs, config.data]);
      setAiConfigModalVisible(false);
      aiConfigForm.resetFields();
      message.success('AI 配置创建成功');
    } catch {
      message.error('创建失败');
    }
  };

  const handlePlay = (campaignId: number) => {
    navigate(`/chat/${campaignId}`);
  };

  const tabItems = [
    {
      key: 'campaigns',
      label: '战役',
      children: (
        <div className="card-grid">
          <Card
            className="add-card"
            hoverable
            onClick={() => setCampaignModalVisible(true)}
          >
            <PlusOutlined className="add-icon" />
            <span>创建战役</span>
          </Card>
          {campaigns.map((campaign) => (
            <Card
              key={campaign.id}
              title={campaign.title}
              extra={
                <Button
                  type="primary"
                  icon={<PlayCircleOutlined />}
                  onClick={() => handlePlay(campaign.id)}
                >
                  开始
                </Button>
              }
            >
              <p>{campaign.description || '暂无描述'}</p>
              <Tag color={campaign.status === 'active' ? 'green' : 'gray'}>
                {campaign.status === 'active' ? '进行中' : '已归档'}
              </Tag>
            </Card>
          ))}
        </div>
      ),
    },
    {
      key: 'characters',
      label: '角色卡',
      children: (
        <div className="card-grid">
          <Card
            className="add-card"
            hoverable
            onClick={() => setCharacterModalVisible(true)}
          >
            <PlusOutlined className="add-icon" />
            <span>创建角色卡</span>
          </Card>
          {characters.map((character) => (
            <Card key={character.id} title={character.name}>
              <p>种族: {character.race || '未知'}</p>
              <p>职业: {character.character_class || '未知'}</p>
              <p>等级: {character.level}</p>
              <p>HP: {character.hp} | AC: {character.ac}</p>
            </Card>
          ))}
        </div>
      ),
    },
    {
      key: 'ai-configs',
      label: 'AI 配置',
      children: (
        <div className="card-grid">
          <Card
            className="add-card"
            hoverable
            onClick={() => setAiConfigModalVisible(true)}
          >
            <PlusOutlined className="add-icon" />
            <span>添加 AI 配置</span>
          </Card>
          {aiConfigs.map((config) => (
            <Card
              key={config.id}
              title={config.provider.toUpperCase()}
              extra={
                config.is_active && <Tag color="gold">使用中</Tag>
              }
            >
              <p>模型: {config.model_name}</p>
              <p>API Key: {config.api_key_masked}</p>
              {config.base_url && <p>端点: {config.base_url}</p>}
            </Card>
          ))}
        </div>
      ),
    },
  ];

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>跑团 KP Agent</h1>
          <p>欢迎, {user?.username}</p>
        </div>
        <div className="header-actions">
          <Button icon={<SettingOutlined />} onClick={() => setAiConfigModalVisible(true)}>
            AI 配置
          </Button>
          <Button onClick={logout}>退出</Button>
        </div>
      </header>

      <Tabs items={tabItems} className="dashboard-tabs" />

      {/* 创建战役 Modal */}
      <Modal
        title="创建战役"
        open={campaignModalVisible}
        onCancel={() => setCampaignModalVisible(false)}
        footer={null}
      >
        <Form form={form} onFinish={handleCreateCampaign} layout="vertical">
          <Form.Item name="title" label="战役名称" rules={[{ required: true }]}>
            <Input placeholder="例如：失落的矿山" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea placeholder="描述你的战役..." />
          </Form.Item>
          <Form.Item name="ai_config_id" label="AI 配置">
            <Select placeholder="选择 AI 配置">
              {aiConfigs.map((config) => (
                <Select.Option key={config.id} value={config.id}>
                  {config.provider.toUpperCase()} - {config.model_name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            创建
          </Button>
        </Form>
      </Modal>

      {/* 创建角色卡 Modal */}
      <Modal
        title="创建角色卡"
        open={characterModalVisible}
        onCancel={() => setCharacterModalVisible(false)}
        footer={null}
      >
        <Form form={characterForm} onFinish={handleCreateCharacter} layout="vertical">
          <Form.Item name="name" label="角色名" rules={[{ required: true }]}>
            <Input placeholder="例如：Gandalf" />
          </Form.Item>
          <Form.Item name="race" label="种族">
            <Select placeholder="选择种族">
              <Select.Option value="人类">人类</Select.Option>
              <Select.Option value="精灵">精灵</Select.Option>
              <Select.Option value="矮人">矮人</Select.Option>
              <Select.Option value="半身人">半身人</Select.Option>
              <Select.Option value="兽人">兽人</Select.Option>
              <Select.Option value="龙裔">龙裔</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="character_class" label="职业">
            <Select placeholder="选择职业">
              <Select.Option value="战士">战士</Select.Option>
              <Select.Option value="法师">法师</Select.Option>
              <Select.Option value="盗贼">盗贼</Select.Option>
              <Select.Option value="牧师">牧师</Select.Option>
              <Select.Option value="游侠">游侠</Select.Option>
              <Select.Option value="吟游诗人">吟游诗人</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="level" label="等级" initialValue={1}>
            <Input type="number" min={1} max={20} />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            创建
          </Button>
        </Form>
      </Modal>

      {/* AI 配置 Modal */}
      <Modal
        title="AI 配置"
        open={aiConfigModalVisible}
        onCancel={() => setAiConfigModalVisible(false)}
        footer={null}
      >
        <Form form={aiConfigForm} onFinish={handleCreateAIConfig} layout="vertical">
          <Form.Item name="provider" label="提供商" rules={[{ required: true }]}>
            <Select placeholder="选择 AI 提供商">
              <Select.Option value="deepseek">DeepSeek</Select.Option>
              <Select.Option value="claude">Claude</Select.Option>
              <Select.Option value="minimax">MiniMax</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item name="api_key" label="API Key" rules={[{ required: true }]}>
            <Input.Password placeholder="输入 API Key" />
          </Form.Item>
          <Form.Item name="base_url" label="自定义端点 (可选)">
            <Input placeholder="例如: https://api.deepseek.com" />
          </Form.Item>
          <Form.Item name="model_name" label="模型名称" rules={[{ required: true }]}>
            <Input placeholder="例如: deepseek-chat" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block>
            保存
          </Button>
        </Form>
      </Modal>
    </div>
  );
}
