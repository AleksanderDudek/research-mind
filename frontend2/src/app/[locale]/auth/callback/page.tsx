import CallbackClient from './_CallbackClient'
export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}
export default function Page() { return <CallbackClient /> }
