import { useEffect, useState, type FormEvent } from 'react'
import {
  createUser,
  deleteUser,
  getUsers,
  updateUser,
  type UpdateUserRequest,
  type User,
} from '../services/api'

interface AdminUsersPanelProps {
  token: string
}

function AdminUsersPanel({ token }: AdminUsersPanelProps) {
  const [users, setUsers] = useState<User[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  const [email, setEmail] = useState('')
  const [realName, setRealName] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState('medical professional')
  const [affiliation, setAffiliation] = useState('')

  const [editingEmail, setEditingEmail] = useState<string | null>(null)
  const [editRealName, setEditRealName] = useState('')
  const [editRole, setEditRole] = useState('')
  const [editAffiliation, setEditAffiliation] = useState('')
  const [editPassword, setEditPassword] = useState('')

  const loadUsers = async () => {
    setIsLoading(true)
    setError('')

    try {
      const result = await getUsers(token)
      setUsers(result)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users.')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadUsers()
  }, [token])

  const handleCreateUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    setError('')
    setMessage('')

    try {
      await createUser(token, {
        email: email.trim(),
        real_name: realName.trim(),
        password,
        role,
        affiliation: affiliation.trim(),
      })

      setEmail('')
      setRealName('')
      setPassword('')
      setRole('medical professional')
      setAffiliation('')
      setMessage('User created successfully.')

      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user.')
    }
  }

  const startEditing = (user: User) => {
    setEditingEmail(user.email)
    setEditRealName(user.real_name)
    setEditRole(user.role)
    setEditAffiliation(user.affiliation)
    setEditPassword('')
    setError('')
    setMessage('')
  }

  const cancelEditing = () => {
    setEditingEmail(null)
    setEditPassword('')
  }

  const handleSaveUser = async (emailToUpdate: string) => {
    setError('')
    setMessage('')

    const updates: UpdateUserRequest = {
      real_name: editRealName.trim(),
      role: editRole,
      affiliation: editAffiliation.trim(),
    }

    if (editPassword.trim()) {
      updates.password = editPassword
    }

    try {
      await updateUser(token, emailToUpdate, updates)

      setEditingEmail(null)
      setEditPassword('')
      setMessage('User updated successfully.')

      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update user.')
    }
  }

  const handleDeleteUser = async (emailToDelete: string) => {
    const confirmed = window.confirm(
      `Delete user ${emailToDelete}?`,
    )

    if (!confirmed) {
      return
    }

    setError('')
    setMessage('')

    try {
      await deleteUser(token, emailToDelete)
      setMessage('User deleted successfully.')

      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user.')
    }
  }

  return (
    <section className="admin-users-panel">
      <div className="admin-users-header">
        <div>
          <h2>User Management</h2>
          <p>Manage authenticated Project Codex users and roles.</p>
        </div>

        <button type="button" onClick={() => void loadUsers()}>
          Refresh
        </button>
      </div>

      {error && (
        <div className="message message--error">
          {error}
        </div>
      )}

      {message && (
        <div className="message message--success">
          {message}
        </div>
      )}

      <div className="admin-create-card">
        <h3>Add User</h3>

        <form className="admin-user-form" onSubmit={handleCreateUser}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <input
            type="text"
            placeholder="Full name"
            value={realName}
            onChange={(event) => setRealName(event.target.value)}
            required
          />

          <input
            type="text"
            placeholder="Affiliation"
            value={affiliation}
            onChange={(event) => setAffiliation(event.target.value)}
            required
          />

          <select
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            <option value="medical professional">
              Medical Professional
            </option>

            <option value="administrator">
              Administrator
            </option>
          </select>

          <input
            type="password"
            placeholder="Temporary password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button type="submit">
            Add User
          </button>
        </form>
      </div>

      <div className="admin-users-table-wrap">
        {isLoading ? (
          <div className="message message--info">
            Loading users...
          </div>
        ) : (
          <table className="admin-users-table">
            <thead>
              <tr>
                <th>Email</th>
                <th>Name</th>
                <th>Affiliation</th>
                <th>Role</th>
                <th>Password</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {users.map((user) => {
                const isEditing = editingEmail === user.email

                return (
                  <tr key={user.email}>
                    <td>{user.email}</td>

                    <td>
                      {isEditing ? (
                        <input
                          value={editRealName}
                          onChange={(event) =>
                            setEditRealName(event.target.value)
                          }
                        />
                      ) : (
                        user.real_name
                      )}
                    </td>

                    <td>
                      {isEditing ? (
                        <input
                          value={editAffiliation}
                          onChange={(event) =>
                            setEditAffiliation(event.target.value)
                          }
                        />
                      ) : (
                        user.affiliation
                      )}
                    </td>

                    <td>
                      {isEditing ? (
                        <select
                          value={editRole}
                          onChange={(event) =>
                            setEditRole(event.target.value)
                          }
                        >
                          <option value="medical professional">
                            Medical Professional
                          </option>

                          <option value="administrator">
                            Administrator
                          </option>
                        </select>
                      ) : (
                        user.role
                      )}
                    </td>

                    <td>
                      {isEditing ? (
                        <input
                          type="password"
                          placeholder="Leave blank to keep"
                          value={editPassword}
                          onChange={(event) =>
                            setEditPassword(event.target.value)
                          }
                        />
                      ) : (
                        '••••••••'
                      )}
                    </td>

                    <td>
                      <div className="admin-user-actions">
                        {isEditing ? (
                          <>
                            <button
                              type="button"
                              onClick={() => void handleSaveUser(user.email)}
                            >
                              Save
                            </button>

                            <button
                              type="button"
                              className="secondary-btn"
                              onClick={cancelEditing}
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={() => startEditing(user)}
                            >
                              Edit
                            </button>

                            <button
                              type="button"
                              className="danger-btn"
                              onClick={() =>
                                void handleDeleteUser(user.email)
                              }
                            >
                              Delete
                            </button>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </section>
  )
}

export default AdminUsersPanel
