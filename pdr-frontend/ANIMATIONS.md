# Page Transition Animations Guide

This guide explains the animation system implemented in your frontend application using Framer Motion.

## Overview

The animation system provides smooth, cinematic transitions between pages and within components. All page transitions are automatically animated using the `PageTransition` component wrapper.

## Animation Types

### 1. **Default Animation** (pageVariants)
Combines fade, scale, and vertical movement for a sophisticated entrance effect.

- **Duration**: 0.6 seconds
- **Effect**: Fade in + scale up + move down
- **Best for**: Home pages, main content areas

```jsx
<PageTransition variant="default">
  <YourPage />
</PageTransition>
```

### 2. **Slide Animation** (slideInVariants)
Smooth slide-in from right with fade effect.

- **Duration**: 0.5 seconds
- **Effect**: Slide in from right + fade
- **Best for**: Multi-step forms, next steps, forward navigation

```jsx
<PageTransition variant="slide">
  <YourPage />
</PageTransition>
```

### 3. **Blur Animation** (blurVariants)
Elegant blur effect with fade-in.

- **Duration**: 0.7 seconds
- **Effect**: Fade in + blur reduction
- **Best for**: Landing pages, special sections

```jsx
<PageTransition variant="blur">
  <YourPage />
</PageTransition>
```

## Using Animations in Components

### AnimatedPage Component
Wraps page content with automatic staggered animations for child elements.

```jsx
import { AnimatedPage, AnimatedSection } from '../components/AnimatedPage'

function MyPage() {
  return (
    <AnimatedPage>
      <AnimatedSection>
        <h1>Title</h1>
      </AnimatedSection>
      <AnimatedSection>
        <p>Description</p>
      </AnimatedSection>
    </AnimatedPage>
  )
}
```

### AnimatedList Component
Perfect for rendering lists with staggered animations.

```jsx
import { AnimatedList } from '../components/AnimatedPage'

function MyList({ items }) {
  return (
    <AnimatedList
      items={items}
      renderItem={(item) => <div>{item.name}</div>}
      className="space-y-4"
    />
  )
}
```

## Animation Variants Available

See `src/animations/animations.js` for all available variants:

- `pageVariants` - Default page transition
- `slideInVariants` - Slide from right
- `slideInLeftVariants` - Slide from left
- `blurVariants` - Blur fade effect
- `scaleVariants` - Scale and fade
- `rotateVariants` - Rotate and scale
- `containerVariants` - For staggered child animations
- `childVariants` - Individual child animations
- `buttonHoverVariants` - Button hover/tap effects
- `cardHoverVariants` - Card hover effects
- `modalVariants` - Modal entrance/exit
- `backdropVariants` - Backdrop animations

## CSS Classes for Animations

Use utility classes for quick animations without Framer Motion:

- `.page-transition` - Page enter animation
- `.slide-in-right` - Slide in from right
- `.slide-in-left` - Slide in from left
- `.scale-in` - Scale in animation
- `.rotate-in` - Rotate and scale
- `.blur-fade-in` - Blur fade effect
- `.animate-gpu` - GPU acceleration
- `.stagger-1` through `.stagger-5` - Animation delays

```jsx
<div className="blur-fade-in">Content</div>
```

## Page Transitions Currently Configured

| Route | Animation | Duration |
|-------|-----------|----------|
| `/` | Blur | 0.7s |
| `/solutions` | Slide | 0.5s |
| `/demo` | Default | 0.6s |
| `/demo-scoring` | Slide | 0.5s |
| `/demo/result/:userId` | Default | 0.6s |
| `/docs` | Blur | 0.7s |

## Best Practices

1. **Use `AnimatePresence`** - Already configured in App.jsx with `mode="wait"` for proper exit animations
2. **Keep durations reasonable** - 0.3-0.7 seconds for page transitions
3. **Use GPU acceleration** - Apply `transform: translateZ(0)` or use `.animate-gpu` class for performance
4. **Stagger children nicely** - `containerVariants` automatically staggers children with 0.1s delay between each
5. **Test on mobile** - Some animations may feel slow on slower devices

## Customization

To modify animation timings or easing, edit `src/animations/animations.js`:

```js
export const pageVariants = {
  animate: {
    transition: {
      duration: 0.6,  // Adjust duration here
      ease: [0.25, 0.46, 0.45, 0.94],  // Adjust easing here
    },
  },
}
```

## Performance Tips

- Use `will-change` CSS property sparingly
- Keep animations under 1 second for UI responsiveness
- Use `transform` and `opacity` for best performance
- GPU acceleration is automatically applied with `transform` changes
