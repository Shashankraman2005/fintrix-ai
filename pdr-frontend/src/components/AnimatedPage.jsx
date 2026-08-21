import { motion } from 'framer-motion'
import { containerVariants, childVariants } from '../animations/animations'

/**
 * AnimatedPage component wraps page content with staggered animations
 * Use this to wrap your page content for consistent animated entry
 * @param {Object} props
 * @param {React.ReactNode} children - Page content
 * @param {string} className - Additional CSS classes
 */
export function AnimatedPage({ children, className = '' }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      exit="exit"
      className={className}
    >
      {children}
    </motion.div>
  )
}

/**
 * AnimatedSection wraps child elements with staggered animation
 * @param {Object} props
 * @param {React.ReactNode} children - Section content
 * @param {string} className - Additional CSS classes
 */
export function AnimatedSection({ children, className = '' }) {
  return (
    <motion.div
      variants={childVariants}
      className={className}
    >
      {children}
    </motion.div>
  )
}

/**
 * Wraps a list of items for staggered animation
 * @param {Object} props
 * @param {Array} items - Items to render
 * @param {Function} renderItem - Render function for each item
 * @param {string} className - Additional CSS classes
 */
export function AnimatedList({ items = [], renderItem, className = '' }) {
  return (
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className={className}
    >
      {items.map((item, index) => (
        <motion.div key={index} variants={childVariants}>
          {renderItem(item, index)}
        </motion.div>
      ))}
    </motion.div>
  )
}
