import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import AuthShell from '../components/layout/AuthShell'
import Button from '../components/ui/Button'
import { Field, Input } from '../components/ui/Input'
import { ErrorBanner } from '../components/ui/ErrorState'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../lib/api'

export default function Register() {
  const { register: registerUser } = useAuth()
  const navigate = useNavigate()
  const [formError, setFormError] = useState('')

  const {
    register,
    handleSubmit,
    setError,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: { first_name: '', username: '', email: '', password: '' },
  })

  const onSubmit = async (values) => {
    setFormError('')
    try {
      await registerUser(values)
      navigate('/dashboard', { replace: true })
    } catch (error) {
      // Map DRF field errors back onto the matching inputs where we can.
      const data = error?.response?.data
      let matched = false
      if (data && typeof data === 'object') {
        for (const field of ['username', 'email', 'password', 'first_name']) {
          if (data[field]) {
            const message = Array.isArray(data[field]) ? data[field][0] : data[field]
            setError(field, { message })
            matched = true
          }
        }
      }
      if (!matched) {
        setFormError(errorMessage(error, 'Could not create your account.'))
      }
    }
  }

  return (
    <AuthShell
      title="Create your account"
      subtitle="Set your first goal in under a minute."
      footer={
        <>
          Already have an account?{' '}
          <Link to="/login" className="font-medium text-brand-600 hover:text-brand-700">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {formError && <ErrorBanner message={formError} />}

        <Field label="First name" htmlFor="first_name" error={errors.first_name?.message}>
          <Input
            id="first_name"
            autoComplete="given-name"
            autoFocus
            placeholder="Manav"
            invalid={Boolean(errors.first_name)}
            {...register('first_name', { required: 'Enter your first name.' })}
          />
        </Field>

        <Field label="Username" htmlFor="username" error={errors.username?.message}>
          <Input
            id="username"
            autoComplete="username"
            placeholder="manav"
            invalid={Boolean(errors.username)}
            {...register('username', {
              required: 'Pick a username.',
              minLength: { value: 3, message: 'At least 3 characters.' },
            })}
          />
        </Field>

        <Field label="Email" htmlFor="email" error={errors.email?.message}>
          <Input
            id="email"
            type="email"
            autoComplete="email"
            placeholder="you@example.com"
            invalid={Boolean(errors.email)}
            {...register('email', {
              required: 'Enter your email.',
              pattern: { value: /\S+@\S+\.\S+/, message: 'That email looks incomplete.' },
            })}
          />
        </Field>

        <Field
          label="Password"
          htmlFor="password"
          error={errors.password?.message}
          hint="At least 8 characters."
        >
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            placeholder="••••••••"
            invalid={Boolean(errors.password)}
            {...register('password', {
              required: 'Choose a password.',
              minLength: { value: 8, message: 'At least 8 characters.' },
            })}
          />
        </Field>

        <Button type="submit" size="lg" className="w-full justify-center" loading={isSubmitting}>
          Create account
        </Button>
      </form>
    </AuthShell>
  )
}
