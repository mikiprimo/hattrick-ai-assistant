import { apiFetch } from './client'

export function initiateOAuth(consumer_key: string, consumer_secret: string): Promise<{ auth_url: string }> {
  return apiFetch('/api/auth/initiate', {
    method: 'POST',
    body: JSON.stringify({ consumer_key, consumer_secret }),
  })
}
