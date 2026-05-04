import SignupClient from './_SignupClient'
export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}
export default function Page() { return <SignupClient /> }
