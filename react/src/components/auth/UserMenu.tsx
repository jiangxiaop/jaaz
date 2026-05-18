import React from 'react'
import { useTranslation } from 'react-i18next'
import { useAuth } from '@/contexts/AuthContext'
import { useConfigs, useRefreshModels } from '@/contexts/configs'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { logout } from '@/api/auth'

export function UserMenu() {
  const { authStatus, refreshAuth } = useAuth()
  const { setShowLoginDialog } = useConfigs()
  const refreshModels = useRefreshModels()
  const { t } = useTranslation()

  const handleLogout = async () => {
    await logout()
    await refreshAuth()
    refreshModels()
  }

  if (authStatus.is_logged_in && authStatus.user_info) {
    const { username, image_url } = authStatus.user_info
    const initials = username ? username.substring(0, 2).toUpperCase() : 'U'

    return (
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative p-0 h-auto">
            <Avatar className="h-6 w-6">
              <AvatarImage src={image_url} alt={username} />
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>{t('common:auth.myAccount')}</DropdownMenuLabel>
          <DropdownMenuItem disabled>{username}</DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={handleLogout}>
            {t('common:auth.logout')}
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    )
  }

  return (
    <Button variant="outline" onClick={() => setShowLoginDialog(true)}>
      {t('common:auth.login')}
    </Button>
  )
}
