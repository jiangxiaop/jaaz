import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Button } from '../ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/dialog'
import { login, register, saveAuthData } from '../../api/auth'
import { useAuth } from '../../contexts/AuthContext'
import { useConfigs, useRefreshModels } from '../../contexts/configs'

export function LoginDialog() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [isRegister, setIsRegister] = useState(false)
  const [loading, setLoading] = useState(false)
  const { refreshAuth } = useAuth()
  const { showLoginDialog: open, setShowLoginDialog } = useConfigs()
  const refreshModels = useRefreshModels()
  const { t } = useTranslation()

  const handleSubmit = async () => {
    setLoading(true)
    setMessage('')
    try {
      const result = isRegister
        ? await register(username, password)
        : await login(username, password)

      if (result.status === 'success' && result.token && result.user_info) {
        saveAuthData(result.token, result.user_info)
        setMessage(t('common:auth.loginSuccessMessage'))
        await refreshAuth()
        refreshModels()
        setTimeout(() => {
          setShowLoginDialog(false)
          setUsername('')
          setPassword('')
          setMessage('')
        }, 1000)
      } else {
        setMessage(result.message || 'Failed')
      }
    } catch {
      setMessage(t('common:auth.loginRequestFailed'))
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && username && password && !loading) {
      handleSubmit()
    }
  }

  return (
    <Dialog open={open} onOpenChange={setShowLoginDialog}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>
            {isRegister ? t('common:auth.register') : t('common:auth.login')}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <input
            type="text"
            placeholder={t('common:auth.username')}
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
            autoFocus
          />
          <input
            type="password"
            placeholder={t('common:auth.password')}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            onKeyDown={handleKeyDown}
            className="w-full rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary"
          />

          {message && (
            <p className="text-sm text-muted-foreground">{message}</p>
          )}

          <Button
            onClick={handleSubmit}
            disabled={loading || !username || !password}
            className="w-full"
          >
            {loading
              ? '...'
              : isRegister
                ? t('common:auth.register')
                : t('common:auth.login')}
          </Button>

          <button
            type="button"
            onClick={() => {
              setIsRegister(!isRegister)
              setMessage('')
            }}
            className="w-full text-center text-sm text-muted-foreground hover:underline"
          >
            {isRegister
              ? t('common:auth.hasAccount')
              : t('common:auth.noAccount')}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  )
}
