import LoginClient from './_LoginClient'
export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}
export default function Page() { return <LoginClient /> }
