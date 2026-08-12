import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import api from '../services/api'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [sent, setSent] = useState(false)
  const [countdown, setCountdown] = useState(0)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const sendCode = async () => {
    if (!/^\+\d{10,}$/.test(phone)) {
      setError('请输入带区号的手机号（如 +8613800138000）')
      return
    }
    setError('')
    try {
      await api.post('/auth/send-code', { phone })
      setSent(true)
      setCountdown(60)
      const timer = setInterval(() => {
        setCountdown((c) => {
          if (c <= 1) {
            clearInterval(timer)
            return 0
          }
          return c - 1
        })
      }, 1000)
    } catch (e) {
      setError(e.response?.data?.detail || '发送失败，请稍后再试')
    }
  }

  const handleLogin = async () => {
    setLoading(true)
    setError('')
    try {
      await login(phone, code)
      navigate('/', { replace: true })
    } catch (e) {
      setError(e.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrap">
      <div className="login-card">
        <div className="logo">流萤 Glimmer</div>
        <p className="tagline">发现你身边隐藏的关系机会</p>

        <div className="field">
          <input
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            placeholder="手机号（+86138...）"
            disabled={sent}
          />
        </div>

        {sent && (
          <div className="field">
            <div className="code-row">
              <input
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="验证码"
                maxLength={6}
              />
              <button className="btn-ghost" disabled={countdown > 0} onClick={sendCode}>
                {countdown > 0 ? `${countdown}s` : '重发'}
              </button>
            </div>
          </div>
        )}

        {!sent ? (
          <button className="btn-primary" onClick={sendCode}>
            获取验证码
          </button>
        ) : (
          <button className="btn-primary" onClick={handleLogin} disabled={loading}>
            {loading ? '登录中...' : '登录'}
          </button>
        )}

        {error && <p className="error">{error}</p>}

        <p className="hint">验证码为 Mock 模式，请查看后端终端日志</p>
      </div>
    </div>
  )
}
