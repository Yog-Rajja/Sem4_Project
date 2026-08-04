import {
  Document,
  Page,
  StyleSheet,
  Text,
  View,
} from '@react-pdf/renderer'

/**
 * Oxford-style academic CV.
 *
 * The conventions being followed: centred name with letter-spacing, a single
 * contact line beneath it, section headings in spaced capitals over a hairline
 * rule, and a narrow left-hand date column against the content. Strictly
 * black on white — no colour, rules, icons or photograph.
 *
 * Times-Roman is one of the PDF standard-14 faces, so it embeds nothing and
 * needs no font file fetched at runtime.
 */
const styles = StyleSheet.create({
  page: {
    paddingTop: 54,
    paddingBottom: 54,
    paddingHorizontal: 62,
    fontFamily: 'Times-Roman',
    fontSize: 10.5,
    lineHeight: 1.45,
    color: '#111111',
  },

  name: {
    fontFamily: 'Times-Roman',
    fontSize: 21,
    textAlign: 'center',
    letterSpacing: 2.6,
    textTransform: 'uppercase',
  },
  headline: {
    fontFamily: 'Times-Italic',
    fontSize: 10.5,
    textAlign: 'center',
    marginTop: 5,
    color: '#333333',
  },
  contact: {
    fontSize: 9.5,
    textAlign: 'center',
    marginTop: 6,
    color: '#333333',
  },

  sectionTitle: {
    fontFamily: 'Times-Bold',
    fontSize: 9.5,
    letterSpacing: 1.7,
    textTransform: 'uppercase',
    marginTop: 17,
    paddingBottom: 3,
    borderBottomWidth: 0.75,
    borderBottomColor: '#111111',
  },

  summary: { marginTop: 8, textAlign: 'justify' },

  // The date column is the load-bearing part of the Oxford look.
  row: { flexDirection: 'row', marginTop: 9 },
  dates: {
    width: 96,
    paddingRight: 10,
    fontSize: 9.5,
    color: '#444444',
  },
  body: { flex: 1 },

  role: { fontFamily: 'Times-Bold', fontSize: 10.5 },
  organisation: { fontFamily: 'Times-Italic', fontSize: 10.5 },
  detail: { fontSize: 10, color: '#333333' },

  bulletRow: { flexDirection: 'row', marginTop: 2.5 },
  bulletMark: { width: 11, fontSize: 10 },
  bulletText: { flex: 1, fontSize: 10, textAlign: 'justify' },

  skillRow: { flexDirection: 'row', marginTop: 4 },
  skillGroup: { width: 96, paddingRight: 10, fontFamily: 'Times-Bold', fontSize: 10 },
  skillItems: { flex: 1, fontSize: 10 },
})

function Section({ title, children }) {
  return (
    <View wrap={false}>
      <Text style={styles.sectionTitle}>{title}</Text>
      {children}
    </View>
  )
}

function Bullets({ items }) {
  return items.map((item, index) => (
    <View style={styles.bulletRow} key={index}>
      <Text style={styles.bulletMark}>•</Text>
      <Text style={styles.bulletText}>{item}</Text>
    </View>
  ))
}

export default function ResumeDocument({ data }) {
  const contact = [data.location, data.phone, data.email]
    .filter(Boolean)
    .join('  ·  ')
  const links = (data.links || []).map((link) => link.url).join('  ·  ')

  return (
    <Document title={`${data.name} CV`} author={data.name}>
      <Page size="A4" style={styles.page}>
        <Text style={styles.name}>{data.name}</Text>
        {data.headline ? <Text style={styles.headline}>{data.headline}</Text> : null}
        {contact ? <Text style={styles.contact}>{contact}</Text> : null}
        {links ? <Text style={styles.contact}>{links}</Text> : null}

        {data.summary ? (
          <Section title="Profile">
            <Text style={styles.summary}>{data.summary}</Text>
          </Section>
        ) : null}

        {data.education?.length ? (
          <Section title="Education">
            {data.education.map((entry, index) => (
              <View style={styles.row} key={index}>
                <Text style={styles.dates}>{entry.period}</Text>
                <View style={styles.body}>
                  <Text style={styles.role}>{entry.qualification}</Text>
                  <Text style={styles.organisation}>{entry.institution}</Text>
                  {entry.detail ? (
                    <Text style={styles.detail}>{entry.detail}</Text>
                  ) : null}
                </View>
              </View>
            ))}
          </Section>
        ) : null}

        {data.experience?.length ? (
          <Section title="Experience">
            {data.experience.map((entry, index) => (
              <View style={styles.row} key={index}>
                <Text style={styles.dates}>{entry.period}</Text>
                <View style={styles.body}>
                  <Text style={styles.role}>{entry.role}</Text>
                  <Text style={styles.organisation}>{entry.organisation}</Text>
                  <Bullets items={entry.bullets || []} />
                </View>
              </View>
            ))}
          </Section>
        ) : null}

        {data.projects?.length ? (
          <Section title="Projects">
            {data.projects.map((entry, index) => (
              <View style={styles.row} key={index}>
                <Text style={styles.dates}>{entry.period}</Text>
                <View style={styles.body}>
                  <Text style={styles.role}>{entry.name}</Text>
                  {entry.description ? (
                    <Text style={styles.bulletText}>{entry.description}</Text>
                  ) : null}
                  {entry.tech?.length ? (
                    <Text style={styles.detail}>{entry.tech.join(', ')}</Text>
                  ) : null}
                </View>
              </View>
            ))}
          </Section>
        ) : null}

        {data.skills?.length ? (
          <Section title="Skills">
            {data.skills.map((group, index) => (
              <View style={styles.skillRow} key={index}>
                <Text style={styles.skillGroup}>{group.group}</Text>
                <Text style={styles.skillItems}>{group.items.join(', ')}</Text>
              </View>
            ))}
          </Section>
        ) : null}

        {data.achievements?.length ? (
          <Section title="Awards and Achievements">
            <Bullets items={data.achievements} />
          </Section>
        ) : null}
      </Page>
    </Document>
  )
}
