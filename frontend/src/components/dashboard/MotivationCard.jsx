import { useCallback, useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Card from '../ui/Card'
import api from '../../lib/api'

const RefreshIcon = ({ size = 16 }) => (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="23 4 23 10 17 10" />
        <polyline points="1 20 1 14 7 14" />
        <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15" />
    </svg>
)

const GRADIENT_SETS = [
    'from-brand-400/20 to-acc-purple/20',
    'from-acc-sky/20 to-acc-mint/20',
    'from-acc-highlight/20 to-brand-400/20',
    'from-acc-purple/20 to-acc-sky/20',
    'from-acc-mint/20 to-acc-highlight/20',
]

export default function MotivationCard() {
    const [quote, setQuote] = useState(null)
    const [refreshing, setRefreshing] = useState(false)
    const [gradientIdx, setGradientIdx] = useState(0)

    const load = useCallback(async (forceFetch = false) => {
        // 1. If not forcing a refresh, try to read from cache first
        if (!forceFetch) {
            try {
                const cachedStr = localStorage.getItem('smart_companion_motivation')
                if (cachedStr) {
                    const parsed = JSON.parse(cachedStr)
                    setQuote(parsed.quoteData)
                    setGradientIdx(parsed.gradientIdx)
                    return // Early return, keep the UI stable
                }
            } catch (e) {
                // Cache read failed, proceed to fetch
            }
        }

        // 2. Otherwise (no cache, or forced refresh), hit the API
        let newQuoteData
        try {
            const { data } = await api.get('/motivation/')
            newQuoteData = data
        } catch {
            newQuoteData = {
                quote: 'The secret of getting ahead is getting started.',
                author: 'Mark Twain',
            }
        }

        const nextIdx = forceFetch
            ? (gradientIdx + 1) % GRADIENT_SETS.length
            : Math.floor(Math.random() * GRADIENT_SETS.length)

        setQuote(newQuoteData)
        setGradientIdx(nextIdx)

        // 3. Save to cache
        localStorage.setItem(
            'smart_companion_motivation',
            JSON.stringify({ quoteData: newQuoteData, gradientIdx: nextIdx })
        )
    }, [gradientIdx]) // gradientIdx dependency so forceFetch can advance it correctly

    useEffect(() => {
        load()
    }, []) // Empty dependency array so it only mounts once

    const handleRefresh = async () => {
        setRefreshing(true)
        await load(true)
        setRefreshing(false)
    }

    if (!quote) return null

    return (
        <Card className={`relative overflow-hidden bg-gradient-to-br ${GRADIENT_SETS[gradientIdx]}`}>
            <div className="px-5 py-5">
                <div className="flex items-center justify-between mb-3">
                    <p className="text-[11.5px] font-semibold tracking-wide text-ink-muted uppercase">
                        ✨ Daily Motivation
                    </p>
                    <motion.button
                        type="button"
                        onClick={handleRefresh}
                        disabled={refreshing}
                        whileHover={{ scale: 1.1 }}
                        whileTap={{ scale: 0.9, rotate: -180 }}
                        className="p-1.5 rounded-xl text-ink-muted hover:text-brand-500 hover:bg-surface/50 transition-colors disabled:opacity-50"
                        title="Get a new quote"
                    >
                        <motion.span
                            animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
                            transition={refreshing ? { duration: 0.6, repeat: Infinity, ease: 'linear' } : {}}
                            className="block"
                        >
                            <RefreshIcon size={14} />
                        </motion.span>
                    </motion.button>
                </div>

                <AnimatePresence mode="wait">
                    <motion.div
                        key={quote.quote}
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -8 }}
                        transition={{ duration: 0.3 }}
                    >
                        <blockquote className="text-[15px] leading-relaxed text-ink font-medium italic">
                            &ldquo;{quote.quote}&rdquo;
                        </blockquote>
                        <p className="mt-3 text-[12.5px] font-semibold text-ink-soft">
                            — {quote.author}
                        </p>
                    </motion.div>
                </AnimatePresence>
            </div>
        </Card>
    )
}
