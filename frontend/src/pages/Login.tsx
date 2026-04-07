import { useNavigate, Link } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import { Button, Input, Form, message } from 'antd';
import './Login.css';

export function Login() {
  const navigate = useNavigate();
  const { login, isLoading } = useAuthStore();
  const [form] = Form.useForm();

  const handleSubmit = async (values: { username: string; password: string }) => {
    try {
      await login(values.username, values.password);
      message.success('登录成功');
      navigate('/');
    } catch {
      message.error('用户名或密码错误');
    }
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">登录</h1>
        <p className="login-subtitle">进入你的跑团世界</p>

        <Form
          form={form}
          onFinish={handleSubmit}
          layout="vertical"
          className="login-form"
        >
          <Form.Item
            name="username"
            rules={[{ required: true, message: '请输入用户名' }]}
          >
            <Input placeholder="用户名" size="large" />
          </Form.Item>

          <Form.Item
            name="password"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="密码" size="large" />
          </Form.Item>

          <Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              loading={isLoading}
              block
              size="large"
            >
              登录
            </Button>
          </Form.Item>
        </Form>

        <div className="login-footer">
          还没有账号？ <Link to="/register">立即注册</Link>
        </div>
      </div>
    </div>
  );
}
