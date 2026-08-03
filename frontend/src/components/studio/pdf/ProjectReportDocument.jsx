import { Document, Page, StyleSheet, Text, View } from '@react-pdf/renderer'

/** Academic report: title block, abstract, numbered sections, references. */
const styles = StyleSheet.create({
  page: {
    paddingTop: 58,
    paddingBottom: 58,
    paddingHorizontal: 64,
    fontFamily: 'Times-Roman',
    fontSize: 10.5,
    lineHeight: 1.55,
    color: '#111111',
  },
  titleBlock: {
    marginBottom: 26,
    paddingBottom: 16,
    borderBottomWidth: 0.75,
    borderBottomColor: '#111111',
  },
  title: {
    fontFamily: 'Times-Bold',
    fontSize: 18,
    textAlign: 'center',
    lineHeight: 1.3,
  },
  subtitle: {
    fontFamily: 'Times-Italic',
    fontSize: 11,
    textAlign: 'center',
    marginTop: 7,
    color: '#333333',
  },
  author: { fontSize: 10.5, textAlign: 'center', marginTop: 10 },

  abstractHeading: {
    fontFamily: 'Times-Bold',
    fontSize: 10,
    letterSpacing: 1.5,
    textTransform: 'uppercase',
    marginBottom: 5,
  },
  abstract: { fontSize: 10, textAlign: 'justify', marginBottom: 6 },

  sectionHeading: {
    fontFamily: 'Times-Bold',
    fontSize: 12,
    marginTop: 16,
    marginBottom: 5,
  },
  body: { textAlign: 'justify' },

  bulletRow: { flexDirection: 'row', marginTop: 3 },
  bulletMark: { width: 13, fontSize: 10 },
  bulletText: { flex: 1, fontSize: 10, textAlign: 'justify' },

  reference: { fontSize: 9.5, marginTop: 3, color: '#222222' },
  pageNumber: {
    position: 'absolute',
    bottom: 30,
    left: 0,
    right: 0,
    textAlign: 'center',
    fontSize: 9,
    color: '#666666',
  },
})

export default function ProjectReportDocument({ data }) {
  return (
    <Document title={data.title} author={data.author}>
      <Page size="A4" style={styles.page}>
        <View style={styles.titleBlock}>
          <Text style={styles.title}>{data.title}</Text>
          {data.subtitle ? <Text style={styles.subtitle}>{data.subtitle}</Text> : null}
          {data.author ? <Text style={styles.author}>{data.author}</Text> : null}
        </View>

        {data.abstract ? (
          <View>
            <Text style={styles.abstractHeading}>Abstract</Text>
            <Text style={styles.abstract}>{data.abstract}</Text>
          </View>
        ) : null}

        {(data.sections || []).map((section, index) => (
          <View key={index}>
            <Text style={styles.sectionHeading}>
              {index + 1}. {section.heading}
            </Text>
            {section.body ? <Text style={styles.body}>{section.body}</Text> : null}
            {(section.bullets || []).map((bullet, bulletIndex) => (
              <View style={styles.bulletRow} key={bulletIndex}>
                <Text style={styles.bulletMark}>•</Text>
                <Text style={styles.bulletText}>{bullet}</Text>
              </View>
            ))}
          </View>
        ))}

        {data.conclusion ? (
          <View>
            <Text style={styles.sectionHeading}>Conclusion</Text>
            <Text style={styles.body}>{data.conclusion}</Text>
          </View>
        ) : null}

        {data.references?.length ? (
          <View>
            <Text style={styles.sectionHeading}>References</Text>
            {data.references.map((reference, index) => (
              <Text style={styles.reference} key={index}>
                [{index + 1}] {reference}
              </Text>
            ))}
          </View>
        ) : null}

        <Text
          style={styles.pageNumber}
          render={({ pageNumber, totalPages }) => `${pageNumber} of ${totalPages}`}
          fixed
        />
      </Page>
    </Document>
  )
}
