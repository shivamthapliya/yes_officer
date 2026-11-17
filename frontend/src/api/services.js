import { ENDPOINTS as E } from '../config/api'
import { api } from './client'

export const authApi = {
  register: (body) => api.post(E.auth.register(), body),
  login: (body) => api.post(E.auth.login(), body),
  logout: () => api.post(E.auth.logout()),
  me: () => api.get(E.auth.me()),
  refresh: () => api.refresh(),
}

export const roomsApi = {
  list: ({ search, page = 1, limit = 24 } = {}) => api.get(E.rooms.list(), { search, page, limit }),
  mine: () => api.get(E.rooms.mine()),
  renameMine: (name) => api.patch(E.rooms.mine(), { name }),
  joined: () => api.get(E.rooms.joined()),
  detail: (roomId) => api.get(E.rooms.detail(roomId)),
  join: (roomId) => api.post(E.rooms.join(roomId)),
  participants: (roomId) => api.get(E.rooms.participants(roomId)),
  activePoll: (roomId) => api.get(E.rooms.activePoll(roomId)),
}

export const pollsApi = {
  list: (roomId, { status, page = 1, limit = 50 } = {}) => api.get(E.rooms.polls(roomId), { status, page, limit }),
  create: (roomId, body) => api.post(E.rooms.polls(roomId), body),
  detail: (pollId) => api.get(E.polls.detail(pollId)),
  update: (pollId, body) => api.patch(E.polls.detail(pollId), body),
  remove: (pollId) => api.delete(E.polls.detail(pollId)),
  addQuestion: (pollId, body) => api.post(E.polls.questions(pollId), body),
  updateQuestion: (questionId, body) => api.patch(E.polls.question(questionId), body),
  removeQuestion: (questionId) => api.delete(E.polls.question(questionId)),
  reorder: (pollId, questionIds) => api.put(E.polls.questionOrder(pollId), { question_ids: questionIds }),
  start: (pollId) => api.post(E.polls.start(pollId)),
  nextQuestion: (pollId) => api.post(E.polls.nextQuestion(pollId)),
  end: (pollId) => api.post(E.polls.end(pollId)),
  cancel: (pollId) => api.post(E.polls.cancel(pollId)),
  live: (pollId) => api.get(E.polls.live(pollId)),
  results: (pollId) => api.get(E.polls.results(pollId)),
  insights: (pollId, questionId) => api.get(E.polls.insights(pollId), { question_id: questionId }),
  studentInsights: (pollId, studentId) => api.get(E.polls.studentInsights(pollId, studentId)),
}

export const answersApi = {
  submit: (pollId, questionId, optionId) =>
    api.post(E.polls.answers(pollId), { question_id: questionId, option_id: optionId }),
}

export const historyApi = {
  myPolls: ({ page = 1, limit = 20 } = {}) => api.get(E.history.myPolls(), { page, limit }),
  review: (pollId) => api.get(E.history.review(pollId)),
}
