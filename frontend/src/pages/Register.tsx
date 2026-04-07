import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import { Button, Input, Form, message } from 'antd';
import './Login.css';

export function Register() {
  const navigate = useNavigate();
  const { register, isLoading } = useAuthStore();
  const [form] = Form.useForm();

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      await register(values.username, values.password);
      message.success('注册成功');
      navigate('/');
    } catch {
      message.error('注册失败，请重试');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">注册</h1>
        <p className="login-subtitle">创建你的跑团账户</p>

        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
          className="login-form"
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true, message: '请输入用户名' },
              { min: 3, message: '用户名至少3个字符' }
            ]}
          >
            <Input placeholder="用户名" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            label="密码"
            rules={[
              { required: true, message: '请输入密码' },
              { min: 6, message: '密码至少6个字符' }
            ]}
          >
            <Input.Password placeholder="密码" size="large" />
          </Form.Item>

          <Form.Item
            name="confirmPassword"
            label="确认密码"
            dependencies={['password']}
            rules={[
              { required: true, message: '请确认密码' },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue('password') === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(new Error('两次输入的密码不一致'));
                },
              }),
            ]}
          >
            <Input.Password placeholder="确认密码" size="large" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              size="large"
            >
              注册
            </Button>
          </Form.Item>
        </Form>

        <div className="login-footer">
          已有账号？ <Link to="/login">立即登录</Link>
        </div>
      </div>
    </div>
  );
}
