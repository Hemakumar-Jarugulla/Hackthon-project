import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Edit3, Shield, UserPlus } from 'lucide-react'
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
import {
  FormField,
  SelectInput,
  TextInput,
} from '../../components/forms/FormField'
import { Modal } from '../../components/modals/Modal'
import { DataTable } from '../../components/tables/DataTable'
import { useToast } from '../../hooks/useToast'
import { analyticsService } from '../../services/analyticsService'
import { formatDateTime } from '../../utils/formatters'

const ROLE_DEFINITIONS = [
  {
    role: 'Marketing Ops Admin',
    permissions: 'Full CRUD across campaigns, costs, attribution runs, validation, and user roles.',
  },
  {
    role: 'Revenue Analyst',
    permissions: 'Read/analyze ROI, attribution comparisons, customer journeys, and export reports.',
  },
  {
    role: 'Campaign Manager',
    permissions: 'Create/edit campaigns, channels, creatives, and target audiences.',
  },
  {
    role: 'Data Steward',
    permissions: 'Triage and resolve exceptions, run validation suites, and verify orders.',
  },
  {
    role: 'Executive Viewer',
    permissions: 'View executive dashboard, revenue analytics, and print reports.',
  },
]

export function UserManagementPage() {
  const { showToast } = useToast()
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [formOpen, setFormOpen] = useState(false)
  const [editing, setEditing] = useState(null)

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm()

  const loadUsers = async () => {
    setLoading(true)
    const data = await analyticsService.listUsers()
    setUsers(data)
    setLoading(false)
  }

  useEffect(() => {
    let active = true
    analyticsService.listUsers().then((data) => {
      if (!active) return
      setUsers(data)
      setLoading(false)
    })
    return () => {
      active = false
    }
  }, [])

  const openModal = (item = null) => {
    setEditing(item)
    reset(
      item || {
        name: '',
        email: '',
        role: 'Revenue Analyst',
        department: 'Revenue Operations',
        status: 'Active',
      }
    )
    setFormOpen(true)
  }

  const onSubmit = async (values) => {
    await analyticsService.saveUser(values, editing?.id || null)
    showToast({
      type: 'success',
      title: editing ? 'User Updated' : 'User Invited',
      message: `${values.name} (${values.role}) saved.`,
    })
    setFormOpen(false)
    await loadUsers()
  }

  const columns = [
    {
      key: 'id',
      label: 'User ID',
      sortable: true,
      render: (r) => <span className="font-mono text-xs font-semibold text-blue-700">{r.id}</span>,
    },
    {
      key: 'name',
      label: 'Name',
      sortable: true,
      render: (r) => (
        <div>
          <p className="font-semibold text-slate-900">{r.name}</p>
          <p className="text-xs text-slate-500">{r.email}</p>
        </div>
      ),
    },
    {
      key: 'role',
      label: 'Role',
      sortable: true,
      render: (r) => <Badge variant="primary">{r.role}</Badge>,
    },
    { key: 'department', label: 'Department', sortable: true },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (r) => (
        <Badge status={r.status === 'Active' ? 'Active' : 'Pending'} dot>
          {r.status}
        </Badge>
      ),
    },
    {
      key: 'lastActive',
      label: 'Last Active',
      sortable: true,
      render: (r) => formatDateTime(r.lastActive),
    },
    {
      key: 'actions',
      label: 'Actions',
      align: 'right',
      render: (r) => (
        <button
          type="button"
          title="Edit user role"
          onClick={() => openModal(r)}
          className="rounded-md p-1.5 text-slate-500 hover:bg-slate-100 hover:text-slate-900 cursor-pointer"
        >
          <Edit3 className="h-4 w-4" />
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        title="User & Role Management"
        description="Manage workspace team access, RBAC roles, and governance permissions."
        badge={<Badge variant="primary">{users.length} Team Members</Badge>}
        actions={
          <Button icon={UserPlus} onClick={() => openModal()}>
            Invite User
          </Button>
        }
      />

      <DataTable columns={columns} data={users} loading={loading} pageSize={10} />

      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Shield className="h-4 w-4 text-blue-600" />
            <div>
              <CardTitle>Role Management Matrix</CardTitle>
              <CardDescription>Access control scopes across AttributionIQ</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
          {ROLE_DEFINITIONS.map((def) => (
            <div
              key={def.role}
              className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-xs"
            >
              <p className="font-bold text-slate-900">{def.role}</p>
              <p className="mt-1 text-slate-600 leading-relaxed">{def.permissions}</p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Modal
        isOpen={formOpen}
        onClose={() => setFormOpen(false)}
        title={editing ? `Edit ${editing.name}` : 'Invite Team Member'}
        footer={
          <>
            <Button variant="outline" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" form="user-form">
              Save User
            </Button>
          </>
        }
      >
        <form id="user-form" onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <FormField label="Full Name" htmlFor="usr-name" required error={errors.name?.message}>
            <TextInput
              id="usr-name"
              hasError={Boolean(errors.name)}
              {...register('name', { required: 'Full name is required.' })}
            />
          </FormField>
          <FormField label="Work Email" htmlFor="usr-email" required error={errors.email?.message}>
            <TextInput
              id="usr-email"
              type="email"
              hasError={Boolean(errors.email)}
              {...register('email', { required: 'Email is required.' })}
            />
          </FormField>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
            <FormField label="Role" htmlFor="usr-role">
              <SelectInput
                id="usr-role"
                options={ROLE_DEFINITIONS.map((d) => ({ value: d.role, label: d.role }))}
                {...register('role')}
              />
            </FormField>
            <FormField label="Department" htmlFor="usr-dept">
              <TextInput id="usr-dept" {...register('department')} />
            </FormField>
            <FormField label="Status" htmlFor="usr-status">
              <SelectInput
                id="usr-status"
                options={[
                  { value: 'Active', label: 'Active' },
                  { value: 'Invited', label: 'Invited' },
                  { value: 'Inactive', label: 'Inactive' },
                ]}
                {...register('status')}
              />
            </FormField>
          </div>
        </form>
      </Modal>
    </div>
  )
}
