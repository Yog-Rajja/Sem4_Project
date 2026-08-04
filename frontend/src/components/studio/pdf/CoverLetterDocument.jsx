import { Document, Page, StyleSheet, Text, View } from '@react-pdf/renderer'

/** Formal British business letter, set to match the Oxford CV. */
const styles = StyleSheet.create({
  page: {
    paddingTop: 62,
    paddingBottom: 62,
    paddingHorizontal: 68,
    fontFamily: 'Times-Roman',
    fontSize: 11,
    lineHeight: 1.6,
    color: '#111111',
  },
  senderBlock: { marginBottom: 26, textAlign: 'right' },
  senderName: { fontFamily: 'Times-Bold', fontSize: 12.5 },
  senderLine: { fontSize: 10, color: '#333333' },

  date: { marginBottom: 18, fontSize: 10.5 },
  recipientBlock: { marginBottom: 18 },
  recipientLine: { fontSize: 10.5 },

  subject: {
    fontFamily: 'Times-Bold',
    fontSize: 11,
    marginBottom: 14,
  },
  greeting: { marginBottom: 12 },
  paragraph: { marginBottom: 11, textAlign: 'justify' },
  closing: { marginTop: 20 },
  signature: { fontFamily: 'Times-Bold', marginTop: 26 },
})

export default function CoverLetterDocument({ data }) {
  const sender = data.sender || {}
  const contact = [sender.location, sender.phone, sender.email].filter(Boolean)

  return (
    <Document title={`Cover letter for ${data.role}`} author={sender.name}>
      <Page size="A4" style={styles.page}>
        <View style={styles.senderBlock}>
          <Text style={styles.senderName}>{sender.name}</Text>
          {contact.map((line) => (
            <Text style={styles.senderLine} key={line}>
              {line}
            </Text>
          ))}
        </View>

        {data.date ? <Text style={styles.date}>{data.date}</Text> : null}

        <View style={styles.recipientBlock}>
          <Text style={styles.recipientLine}>{data.recipient}</Text>
          {data.company ? (
            <Text style={styles.recipientLine}>{data.company}</Text>
          ) : null}
        </View>

        {data.role ? (
          <Text style={styles.subject}>
            Re: Application for {data.role}
            {data.company ? ` at ${data.company}` : ''}
          </Text>
        ) : null}

        <Text style={styles.greeting}>{data.greeting}</Text>

        {(data.paragraphs || []).map((paragraph, index) => (
          <Text style={styles.paragraph} key={index}>
            {paragraph}
          </Text>
        ))}

        <Text style={styles.closing}>{data.closing}</Text>
        <Text style={styles.signature}>{sender.name}</Text>
      </Page>
    </Document>
  )
}
