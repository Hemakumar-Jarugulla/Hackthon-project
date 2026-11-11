import { useForm } from 'react-hook-form'
import { KeyRound, Save, ShieldCheck } from 'lucide-react'
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PageHeader,
} from '../../components/common'
import { FormField, TextInput } from '../../components/forms/FormField'
import { useAuth } from '../../hooks/useAuth'
import { useToast } from '../../hooks/useToast'

export function ProfilePage() {
  const { user, isMockMode, updateProfile } = useAuth()
  const { showToast } = useToast()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    defaultValues: {
      name: user?.name || '',
      email: user?.email || '',
      department: user?.department || 'Revenue Operations',
      timezone: user?.timezone || 'UTC+05:30',
    },
  })

  const onSaveProfile = async (values) => {
    await updateProfile(values)
    showToast({
      type: 'success',
      title: 'Profile Updated',
      message: 'Your account details have been saved.',
    })
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="User Profile"
        description="Manage your personal identity, department metadata, and session security."
        badge={<Badge variant="primary" dot>{user?.role}</Badge>}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div>
              <CardTitle>Profile Details</CardTitle>
              <CardDescription>Persisted cleanly in mock auth session</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSaveProfile)} className="space-y-4">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField
                  label="Full Name"
                  htmlFor="prof-name"
                  required
                  error={errors.name?.message}
                >
                  <TextInput
                    id="prof-name"
                    hasError={Boolean(errors.name)}
                    {...register('name', { required: 'Name is required.' })}
                  />
                </FormField>
                <FormField
                  label="Work Email"
                  htmlFor="prof-email"
                  required
                  error={errors.email?.message}
                >
                  <TextInput
                    id="prof-email"
                    type="email"
                    hasError={Boolean(errors.email)}
                    {...register('email', { required: 'Email is required.' })}
                  />
                </FormField>
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <FormField label="Department" htmlFor="prof-dept">
                  <TextInput id="prof-dept" {...register('department')} />
                </FormField>
                <FormField label="Timezone" htmlFor="prof-tz">
                  <TextInput id="prof-tz" {...register('timezone')} />
                </FormField>
              </div>

              <div className="flex justify-end pt-2">
                <Button type="submit" icon={Save}>
                  Update Profile
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-emerald-600" />
              <CardTitle>Authentication Session</CardTitle>
            </div>
          </CardHeader>
          <CardContent className="space-y-3 text-xs">
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">User ID</span>
              <span className="font-mono font-semibold text-slate-900">{user?.id}</span>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Assigned Role</span>
              <Badge variant="primary">{user?.role}</Badge>
            </div>
            <div className="flex justify-between border-b border-slate-100 pb-2">
              <span className="text-slate-500">Auth Adapter</span>
              <span className="font-semibold text-emerald-700">
                {isMockMode ? 'Mock JWT Ready' : 'Live Django SimpleJWT'}
              </span>
            </div>
            <Button
              variant="outline"
              size="sm"
              icon={KeyRound}
              className="w-full mt-2"
              onClick={() =>
                showToast({
                  type: 'info',
                  title: 'Password Rotation',
                  message: 'Password reset flow ready for Django JWT auth endpoint.',
                })
              }
            >
              Simulate Password Rotation
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

