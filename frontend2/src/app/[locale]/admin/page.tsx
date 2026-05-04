import AdminClient from './_AdminClient'
export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}
export default function Page() { return <AdminClient /> }
