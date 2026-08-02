import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import AuthShell from '../components/layout/AuthShell'
import Button from '../components/ui/Button'
import { Field, Input } from '../components/ui/Input'
import { ErrorBanner } from '../components/ui/ErrorState'
import { useAuth } from '../context/AuthContext'
import { errorMessage } from '../lib/api'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [formError, setFormError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({ defaultValues: { username: '', password: '' } })

  const onSubmit = async (values) => {
    setFormError('')
    try {
      await login(values)
      navigate(location.state?.from?.pathname || '/dashboard', { replace: true })
    } catch (error) {
      setFormError(
        error?.response?.status === 401
          ? 'That username and password combination did not work.'
          : errorMessage(error, 'Could not sign you in. Please try again.'),
      )
    }
  }

  return (
    <AuthShell
      title="Welcome back"
      subtitle="Sign in to pick up where you left off."
      footer={
        <>
          New here?{' '}
          <Link to="/register" className="font-medium text-brand-600 hover:text-brand-700">
            Create an account
          </Link>
        </>
      }
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
        {formError && <ErrorBanner message={formError} />}

        <Field label="Username" htmlFor="username" error={errors.username?.message}>
          <Input
            id="username"
            autoComplete="username"
            autoFocus
            placeholder="your username"
            invalid={Boolean(errors.username)}
            {...register('username', { required: 'Enter your username.' })}
          />
        </Field>

        <Field label="Password" htmlFor="password" error={errors.password?.message}>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            placeholder="••••••••"
            invalid={Boolean(errors.password)}
            {...register('password', { required: 'Enter your password.' })}
          />
        </Field>

        <Button type="submit" size="lg" className="w-full justify-center" loading={isSubmitting}>
          Sign in
        </Button>
      </form>
    </AuthShell>
  )
}
