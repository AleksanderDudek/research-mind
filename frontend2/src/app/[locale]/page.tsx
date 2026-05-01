import HomeClient from './_HomeClient'

export function generateStaticParams() {
  return [{ locale: 'en' }, { locale: 'pl' }]
}

export default function Page() {
  return <HomeClient />
}
