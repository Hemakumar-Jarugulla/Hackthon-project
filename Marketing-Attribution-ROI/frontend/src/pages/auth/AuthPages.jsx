import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { KeyRound, LogIn, MailCheck, UserPlus } from 'lucide-react'
import { Button } from '../../components/common'
import {
  FormField,
  SelectInput,
  TextInput,
} from '../../components/forms/FormField'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'

export function LoginPage() {
  const navigate = useNavigate()
  const { login, isMockMode } = useAuth()
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm({
    defaultValues: {
      email: 'alex.morgan@attributioniq.io',
      password: 'demo-password',
    },
  })

  const onSubmit = async (values) => {
    try {
      await login({ email: values.email, password: values.password })
      showToast({
        type: 'success',
        title: 'Signed In',
        message: `Welcome back, ${values.email}`,
      })
      navigate('/dashboard')
    } catch (err) {
      showToast({
        type: 'error',
        title: 'Authentication Failed',
        message: err?.response?.data?.error?.message || 'Invalid credentials.',
      })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Sign in to workspace</h2>
        <p className="mt-1 text-xs text-slate-500">
          {isMockMode
            ? 'Mock authentication active — switch VITE_USE_MOCK_DATA=false for live Django JWT.'
            : 'Connected to Django REST SimpleJWT authentication endpoint.'}
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          label="Work Email"
          htmlFor="login-email"
          required
          error={errors.email?.message}
        >
          <TextInput
            id="login-email"
            type="email"
            hasError={Boolean(errors.email)}
            {...register('email', { required: 'Work email is required.' })}
          />
        </FormField>

        <FormField
          label="Password"
          htmlFor="login-password"
          required
          error={errors.password?.message}
        >
          <TextInput
            id="login-password"
            type="password"
            hasError={Boolean(errors.password)}
            {...register('password', { required: 'Password is required.' })}
          />
        </FormField>

        <div className="flex items-center justify-between text-xs">
          <Link
            to="/forgot-password"
            className="font-semibold text-blue-600 hover:text-blue-700"
          >
            Forgot password?
          </Link>
          <Link
            to="/register"
            className="font-medium text-slate-600 hover:text-slate-900"
          >
            Create account
          </Link>
        </div>

        <Button type="submit" icon={LogIn} className="w-full" size="lg" disabled={isSubmitting}>
          {isSubmitting ? 'Signing In...' : 'Sign In'}
        </Button>
      </form>
    </div>
  )
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { register: registerUser } = useAuth()
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      name: '',
      email: '',
      role: 'Marketing Ops Admin',
      password: '',
    },
  })

  const onSubmit = async (values) => {
    try {
      await registerUser(values)
      showToast({
        type: 'success',
        title: 'Account Created',
        message: 'Workspace profile created successfully.',
      })
      navigate('/dashboard')
    } catch (err) {
      showToast({
        type: 'error',
        title: 'Registration Failed',
        message: err?.response?.data?.error?.message || 'Unable to create account.',
      })
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Create an account</h2>
        <p className="mt-1 text-xs text-slate-500">
          Join your marketing operations workspace on AttributionIQ.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          label="Full Name"
          htmlFor="reg-name"
          required
          error={errors.name?.message}
        >
          <TextInput
            id="reg-name"
            placeholder="Jordan Taylor"
            hasError={Boolean(errors.name)}
            {...register('name', { required: 'Full name is required.' })}
          />
        </FormField>

        <FormField
          label="Work Email"
          htmlFor="reg-email"
          required
          error={errors.email?.message}
        >
          <TextInput
            id="reg-email"
            type="email"
            placeholder="jordan@company.com"
            hasError={Boolean(errors.email)}
            {...register('email', { required: 'Email is required.' })}
          />
        </FormField>

        <FormField label="Role" htmlFor="reg-role">
          <SelectInput
            id="reg-role"
            options={[
              { value: 'Marketing Ops Admin', label: 'Marketing Ops Admin' },
              { value: 'Revenue Analyst', label: 'Revenue Analyst' },
              { value: 'Campaign Manager', label: 'Campaign Manager' },
              { value: 'Executive Viewer', label: 'Executive Viewer' },
            ]}
            {...register('role')}
          />
        </FormField>

        <FormField
          label="Password"
          htmlFor="reg-password"
          required
          error={errors.password?.message}
        >
          <TextInput
            id="reg-password"
            type="password"
            placeholder="Minimum 6 characters"
            hasError={Boolean(errors.password)}
            {...register('password', {
              required: 'Password is required.',
              minLength: { value: 6, message: 'At least 6 characters.' },
            })}
          />
        </FormField>

        <Button type="submit" icon={UserPlus} className="w-full" size="lg">
          Create Workspace Account
        </Button>
      </form>

      <p className="text-center text-xs text-slate-600">
        Already have an account?{' '}
        <Link
          to="/login"
          className="font-semibold text-blue-600 hover:text-blue-700"
        >
          Sign in
        </Link>
      </p>
    </div>
  )
}

export function ForgotPasswordPage() {
  const [sentTo, setSentTo] = useState('')
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm()

  const onSubmit = (values) => {
    setSentTo(values.email)
    showToast({
      type: 'info',
      title: 'Reset Link Simulated',
      message: `Password reset instructions prepared for ${values.email}.`,
    })
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Reset your password</h2>
        <p className="mt-1 text-xs text-slate-500">
          Enter your account email and we will simulate sending a reset link.
        </p>
      </div>

      {sentTo ? (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-xs text-emerald-800 space-y-3">
          <div className="flex items-center gap-2 font-semibold">
            <MailCheck className="h-4 w-4 text-emerald-600" />
            <span>Reset link sent to {sentTo}</span>
          </div>
          <p>
            Proceed to the reset password screen to test setting a new password.
          </p>
          <Link
            to="/reset-password"
            className="inline-block font-semibold text-blue-700 underline"
          >
            Continue to Reset Password
          </Link>
        </div>
      ) : (
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField
            label="Work Email"
            htmlFor="forgot-email"
            required
            error={errors.email?.message}
          >
            <TextInput
              id="forgot-email"
              type="email"
              placeholder="alex.morgan@attributioniq.io"
              hasError={Boolean(errors.email)}
              {...register('email', { required: 'Email is required.' })}
            />
          </FormField>
          <Button type="submit" icon={KeyRound} className="w-full" size="lg">
            Send Reset Link
          </Button>
        </form>
      )}

      <p className="text-center text-xs text-slate-600">
        Remembered your password?{' '}
        <Link
          to="/login"
          className="font-semibold text-blue-600 hover:text-blue-700"
        >
          Back to sign in
        </Link>
      </p>
    </div>
  )
}

export function ResetPasswordPage() {
  const navigate = useNavigate()
  const { showToast } = useToast()
  const {
    register,
    handleSubmit,
    getValues,
    formState: { errors },
  } = useForm()

  const onSubmit = () => {
    showToast({
      type: 'success',
      title: 'Password Updated',
      message: 'Mock password updated. You can now sign in.',
    })
    navigate('/login')
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-bold text-slate-900">Set new password</h2>
        <p className="mt-1 text-xs text-slate-500">
          Choose a strong password for your AttributionIQ account.
        </p>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <FormField
          label="New Password"
          htmlFor="reset-password"
          required
          error={errors.password?.message}
        >
          <TextInput
            id="reset-password"
            type="password"
            hasError={Boolean(errors.password)}
            {...register('password', {
              required: 'New password is required.',
              minLength: { value: 6, message: 'At least 6 characters.' },
            })}
          />
        </FormField>

        <FormField
          label="Confirm Password"
          htmlFor="reset-confirm"
          required
          error={errors.confirmPassword?.message}
        >
          <TextInput
            id="reset-confirm"
            type="password"
            hasError={Boolean(errors.confirmPassword)}
            {...register('confirmPassword', {
              required: 'Please confirm your password.',
              validate: (val) =>
                val === getValues('password') || 'Passwords do not match.',
            })}
          />
        </FormField>

        <Button type="submit" icon={KeyRound} className="w-full" size="lg">
          Update Password
        </Button>
      </form>
    </div>
  )
}

