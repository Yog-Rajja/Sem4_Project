import jsPDF from 'jspdf'
import autoTable from 'jspdf-autotable'

export default function generateReport(data) {
    const doc = new jsPDF()
    const now = new Date()
    const dateStr = now.toLocaleDateString('en-IN', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
    })

    // --- Page 1: Header + Overall Stats ---
    doc.setFontSize(22)
    doc.setFont('helvetica', 'bold')
    doc.text('Smart Companion', 14, 22)

    doc.setFontSize(11)
    doc.setFont('helvetica', 'normal')
    doc.setTextColor(120)
    doc.text('Analytics Report', 14, 30)
    doc.text(`Generated on ${dateStr}`, 14, 36)
    doc.setTextColor(0)

    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Overall Statistics', 14, 50)

    autoTable(doc, {
        startY: 55,
        head: [['Metric', 'Value']],
        body: [
            ['Total Tasks', String(data.overall.total)],
            ['Completed', String(data.overall.completed)],
            ['Pending', String(data.overall.pending)],
            ['Completion Rate', `${data.overall.progress}%`],
            ['Current Streak', `${data.streaks.current} day${data.streaks.current !== 1 ? 's' : ''}`],
            ['Best Streak', `${data.streaks.best} day${data.streaks.best !== 1 ? 's' : ''}`],
        ],
        theme: 'striped',
        headStyles: { fillColor: [255, 107, 107] },
        styles: { fontSize: 10 },
    })

    // --- Status Breakdown ---
    const statusY = doc.lastAutoTable.finalY + 12
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Task Status Breakdown', 14, statusY)

    autoTable(doc, {
        startY: statusY + 5,
        head: [['Status', 'Count', 'Percentage']],
        body: data.status_breakdown.map((s) => {
            const pct = data.overall.total
                ? Math.round((s.value / data.overall.total) * 100)
                : 0
            return [s.name, String(s.value), `${pct}%`]
        }),
        theme: 'striped',
        headStyles: { fillColor: [90, 200, 250] },
        styles: { fontSize: 10 },
    })

    // --- Page 2: Per-Goal Progress ---
    doc.addPage()
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Progress by Goal', 14, 22)

    if (data.per_goal.length > 0) {
        autoTable(doc, {
            startY: 28,
            head: [['Goal', 'Completed', 'Total', 'Progress']],
            body: data.per_goal.map((g) => [
                g.title,
                String(g.completed),
                String(g.total),
                `${g.progress}%`,
            ]),
            theme: 'striped',
            headStyles: { fillColor: [155, 109, 255] },
            styles: { fontSize: 10 },
            columnStyles: { 0: { cellWidth: 85 } },
        })
    } else {
        doc.setFontSize(11)
        doc.setFont('helvetica', 'normal')
        doc.text('No goals with tasks yet.', 14, 32)
    }

    // --- Workload ---
    const wlY = data.per_goal.length > 0 ? doc.lastAutoTable.finalY + 12 : 44
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Upcoming Workload (Next 14 Days)', 14, wlY)

    const workloadRows = data.workload.filter((w) => w.count > 0)
    if (workloadRows.length > 0) {
        autoTable(doc, {
            startY: wlY + 5,
            head: [['Date', 'Tasks Due']],
            body: workloadRows.map((w) => [w.label, String(w.count)]),
            theme: 'striped',
            headStyles: { fillColor: [97, 232, 178] },
            styles: { fontSize: 10 },
        })
    } else {
        doc.setFontSize(11)
        doc.setFont('helvetica', 'normal')
        doc.text('No upcoming tasks due in the next 14 days.', 14, wlY + 8)
    }

    // --- Daily Completions ---
    const dcY = workloadRows.length > 0 ? doc.lastAutoTable.finalY + 12 : wlY + 20
    doc.setFontSize(14)
    doc.setFont('helvetica', 'bold')
    doc.text('Daily Completions (Past 14 Days)', 14, dcY)

    const completionRows = data.daily_completions.filter((d) => d.count > 0)
    if (completionRows.length > 0) {
        autoTable(doc, {
            startY: dcY + 5,
            head: [['Date', 'Tasks Completed']],
            body: completionRows.map((d) => [d.label, String(d.count)]),
            theme: 'striped',
            headStyles: { fillColor: [255, 217, 61] },
            styles: { fontSize: 10 },
        })
    } else {
        doc.setFontSize(11)
        doc.setFont('helvetica', 'normal')
        doc.text('No tasks completed in the past 14 days.', 14, dcY + 8)
    }

    // --- Footer on each page ---
    const pageCount = doc.internal.getNumberOfPages()
    for (let i = 1; i <= pageCount; i++) {
        doc.setPage(i)
        doc.setFontSize(8)
        doc.setTextColor(150)
        doc.text(
            `Smart Companion Analytics Report — Page ${i} of ${pageCount}`,
            14,
            doc.internal.pageSize.height - 10,
        )
    }

    doc.save(`Smart_Companion_Report_${now.toISOString().slice(0, 10)}.pdf`)
}
