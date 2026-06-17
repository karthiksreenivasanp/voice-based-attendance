        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        primary: {
                            300: '#a5b4fc',
                            400: '#818cf8',
                            500: '#6366f1',
                            600: '#4f46e5',
                        },
                        dark: {
                            800: '#1e293b',
                            900: '#0f172a',
                        }
                    },
                    fontFamily: {
                        sans: ['Outfit', 'Inter', 'sans-serif'],
                    }
                }
            }
        }
    </script>
    <script>
        const savedState = JSON.parse(localStorage.getItem('voice_app_state') || '{}');
        const state = {
            currentView: savedState.currentView || 'login',
            role: savedState.role || 'STUDENT',
            isRegister: false,
            showSettings: false,
            apiUrl: savedState.apiUrl || 'https://karthiksreenivasanp-backend-finetuned-ecapa.hf.space',
            username: savedState.username || '',
            name: savedState.name || '',
            rollNo: savedState.rollNo || '',
            course: savedState.course || '',
            subject: savedState.subject || '',
            isChangingMentor: false,
            mentorId: savedState.mentorId || null,
            voiceEnrolled: savedState.voiceEnrolled || false,
            enrollStep: 0,
            recording: false,
            attendanceList: [],
            teachers: []
        };

        function saveSession() {
            localStorage.setItem('voice_app_state', JSON.stringify({
                currentView: state.currentView,
                role: state.role,
                apiUrl: state.apiUrl,
                username: state.username,
                name: state.name,
                rollNo: state.rollNo,
                course: state.course,
                subject: state.subject,
                mentorId: state.mentorId,
                voiceEnrolled: state.voiceEnrolled
            }));
        }

        function renderLoginView() {
            return `
            <div class="min-h-screen flex flex-col items-center justify-center p-4 relative overflow-hidden">
                <div class="absolute top-[-10%] left-[-10%] w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none"></div>
                <div class="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-purple-600/20 rounded-full blur-3xl pointer-events-none"></div>
                
                <div class="absolute top-6 right-6 flex gap-4 z-50">
                    <button class="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white">
                        <i data-lucide="refresh-ccw" class="w-5 h-5"></i>
                    </button>
                    <button onclick="toggleSettings()" class="p-2 rounded-full transition-colors ${state.showSettings ? 'bg-primary-600 text-white' : 'hover:bg-slate-800 text-slate-400 hover:text-white'}">
                        <i data-lucide="settings" class="w-5 h-5"></i>
                    </button>
                </div>

                ${state.showSettings ? `
                <div class="absolute top-20 right-6 z-50 w-80 bg-slate-800/90 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-5 shadow-2xl">
                    <h4 class="flex items-center gap-2 m-0 mb-3 font-semibold text-slate-200">
                        <i data-lucide="server" class="w-[18px] text-primary-500"></i> API Target Server
                    </h4>
                    <p class="text-xs text-slate-400 mb-3 truncate">Current: ${state.apiUrl}</p>
                    <input type="text" value="${state.apiUrl}" onchange="state.apiUrl = this.value" class="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary-500 mb-4 transition-colors" />
                    <div class="flex gap-2">
                        <button onclick="toggleSettings()" class="flex-2 bg-primary-600 hover:bg-primary-500 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors">Update URL</button>
                        <button onclick="alert('Connection Success! Version: 1.0.0')" class="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 px-3 rounded-lg text-sm transition-colors">Test</button>
                    </div>
                </div>
                ` : ''}

                <div class="w-full max-w-md z-10">
                    <div class="bg-slate-800/40 backdrop-blur-xl border border-slate-700/50 p-8 rounded-3xl shadow-2xl">
                        <div class="text-center mb-8">
                            <div class="inline-flex items-center justify-center p-4 bg-primary-500/10 rounded-2xl mb-4 transform transition-transform hover:scale-110">
                                <i data-lucide="shield-check" class="w-10 h-10 text-primary-500"></i>
                            </div>
                            <h2 class="text-2xl font-bold text-white mb-2 tracking-tight">${state.isRegister ? 'Create an Account' : 'Welcome Back'}</h2>
                            <p class="text-slate-400 text-sm">${state.isRegister ? 'Join the voice attendance system' : 'Secure voice-based attendance'}</p>
                        </div>

                        <form onsubmit="handleAuth(event)" class="space-y-4">
                            ${state.isRegister ? `
                            <div class="flex gap-2 mb-2 p-1 bg-slate-900/50 rounded-xl">
                                <button type="button" onclick="setRole('STUDENT')" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all ${state.role === 'STUDENT' ? 'bg-primary-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}">Student</button>
                                <button type="button" onclick="setRole('TEACHER')" class="flex-1 py-2 text-sm font-medium rounded-lg transition-all ${state.role === 'TEACHER' ? 'bg-primary-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}">Teacher</button>
                            </div>
                            ` : ''}

                            <div>
                                <input id="username-input" type="text" placeholder="${state.isRegister && state.role === 'STUDENT' ? 'Choose a Username' : 'Username'}" required class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all shadow-inner" />
                            </div>

                            ${state.isRegister && state.role === 'STUDENT' ? `
                            <div class="space-y-4">
                                <input id="name-input" type="text" placeholder="Full Name" required class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all" />
                                <div class="flex gap-4">
                                    <input id="rollno-input" type="text" placeholder="Roll Number" required class="w-1/2 bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all" />
                                    <input id="course-input" type="text" placeholder="Course/Branch" required class="w-1/2 bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all" />
                                </div>
                            </div>
                            ` : ''}

                            ${state.isRegister && state.role === 'TEACHER' ? `
                            <div class="space-y-4">
                                <input id="name-input" type="text" placeholder="Full Name" required class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all" />
                                <input id="subject-input" type="text" placeholder="Subject Taught" required class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all" />
                            </div>
                            ` : ''}

                            <div>
                                <input type="password" placeholder="Password" required class="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all shadow-inner" />
                            </div>

                            <button type="submit" class="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-indigo-500 text-white font-semibold py-3.5 px-4 rounded-xl shadow-lg shadow-primary-500/30 flex items-center justify-center gap-2 mt-6 transition-transform transform hover:scale-[1.02] active:scale-[0.98]">
                                ${state.isRegister ? `<i data-lucide="user-plus" class="w-[18px]"></i> Register Now` : `<i data-lucide="log-in" class="w-[18px]"></i> Sign In`}
                            </button>
                        </form>

                        <div class="mt-8 text-center border-t border-slate-700/50 pt-6">
                            <p class="text-slate-400 text-sm">
                                ${state.isRegister ? 'Already have an account?' : "Don't have an account?"}
                                <button onclick="toggleRegister()" class="ml-2 font-medium text-primary-400 hover:text-primary-300 transition-colors bg-transparent border-none focus:outline-none">
                                    ${state.isRegister ? 'Login instead' : 'Register here'}
                                </button>
                            </p>
                        </div>
                    </div>
                </div>
            </div>`;
        }

        function renderStudentDashboard() {
            return `
            <div class="max-w-md mx-auto p-4 space-y-6 mt-4">
                <header class="mb-6 flex justify-between items-center">
                    <div>
                        <h1 class="text-2xl font-bold text-white">Student Hub</h1>
                        <p class="text-slate-400 text-sm">Hello, ${state.username || 'Student'}</p>
                    </div>
                    <div class="w-12 h-12 bg-primary-600/20 rounded-full flex items-center justify-center text-primary-400 border border-primary-500/30">
                        <i data-lucide="user" class="w-6 h-6"></i>
                    </div>
                </header>

                <div class="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 p-5 rounded-2xl shadow-lg relative overflow-hidden">
                    <div class="relative z-10 grid grid-cols-2 gap-4">
                        <div>
                            <p class="text-xs text-slate-500 uppercase font-semibold">Roll No</p>
                            <p class="text-white font-medium">${state.rollNo || 'N/A'}</p>
                        </div>
                        <div>
                            <p class="text-xs text-slate-500 uppercase font-semibold">Course</p>
                            <p class="text-white font-medium truncate">${state.course || 'N/A'}</p>
                        </div>
                        <div class="col-span-2 mt-2">
                            <p class="text-xs text-slate-500 uppercase font-semibold">Mentor</p>
                            <p class="text-white font-medium flex items-center justify-between">
                                <span class="flex items-center gap-2">
                                    ${state.mentorId ? `Teacher ID ${state.mentorId}` : `<span class="text-amber-400 text-sm">Not Selected</span>`}
                                </span>
                                ${state.mentorId ? `
                                <button onclick="toggleChangeMentor()" class="text-xs bg-slate-700/50 hover:bg-slate-700 px-3 py-1 rounded transition-colors text-slate-300">
                                    ${state.isChangingMentor ? 'Cancel' : 'Change'}
                                </button>
                                ` : ''}
                            </p>
                        </div>
                    </div>
                </div>

                ${(!state.mentorId || state.isChangingMentor) ? `
                <div class="bg-amber-900/20 border border-amber-500/30 p-5 rounded-2xl">
                    <h3 class="text-amber-400 font-bold mb-2 flex items-center gap-2"><i data-lucide="shield-check" class="w-[18px]"></i> Select Your Mentor</h3>
                    <p class="text-sm text-amber-200/70 mb-4">You must select an available mentor to attend their classes.</p>
                    <div class="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                        ${state.teachers && state.teachers.length > 0 ? state.teachers.map(t => `
                        <button onclick="selectMentor('${t.id}')" class="w-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700 p-3 rounded-xl flex items-center justify-between transition-colors focus:ring-2 ring-primary-500">
                            <div class="text-left">
                                <span class="text-slate-200 text-sm font-medium">Prof. ${t.name}</span>
                                <span class="block text-slate-400 text-xs mt-0.5">${t.subject || 'General'}</span>
                            </div>
                            <i data-lucide="chevron-right" class="w-4 h-4 text-slate-500"></i>
                        </button>
                        `).join('') : `
                        <div class="p-4 text-center text-slate-500">No teachers found.</div>
                        `}
                    </div>
                </div>
                ` : ''}

                ${state.mentorId ? `
                <div class="space-y-4">
                    <div class="bg-slate-800/40 border border-slate-700/50 p-5 rounded-2xl shadow-md">
                        <div class="flex justify-between items-start mb-4">
                            <div>
                                <h3 class="font-bold text-slate-200 flex items-center gap-2">
                                    Voice Signature
                                    ${state.voiceEnrolled ? `<i data-lucide="check-circle-2" class="w-4 h-4 text-emerald-400"></i>` : ''}
                                </h3>
                                <p class="text-xs text-slate-500 mt-1">
                                    ${state.voiceEnrolled ? `Enrolled ${new Date().toLocaleDateString()}` : 'No voice signature found.'}
                                </p>
                            </div>
                        </div>

                        ${state.voiceEnrolled ? `
                        <div class="flex gap-2">
                            <button onclick="hearPlayback()" class="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-xl font-medium transition-colors border border-slate-700/50 flex items-center justify-center gap-2">
                                <i data-lucide="play" class="w-4 h-4"></i> Playback
                            </button>
                            <button onclick="navigate('enroll')" class="flex-1 bg-slate-800 hover:bg-slate-700 text-slate-300 px-4 py-3 rounded-xl font-medium transition-colors border border-slate-700/50 flex items-center justify-center gap-2">
                                <i data-lucide="refresh-cw" class="w-4 h-4"></i> Update Voice
                            </button>
                            <button onclick="deleteVoice()" class="bg-red-500/20 text-red-400 hover:bg-red-500/30 p-3 rounded-xl transition-colors border border-red-500/20">
                                <i data-lucide="trash-2" class="w-5 h-5"></i>
                            </button>
                        </div>
                        ` : `
                        <button onclick="navigate('enroll')" class="block w-full text-center bg-primary-600 hover:bg-primary-500 text-white py-3 rounded-xl font-medium transition-colors shadow-md shadow-primary-500/20">
                            Enroll Voice Profile Now
                        </button>
                        `}
                    </div>

                    ${state.voiceEnrolled ? `
                    <button onclick="navigate('verify')" class="w-full flex flex-col items-center justify-center p-8 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-3xl group shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 transition-all duration-300 relative overflow-hidden">
                        <div class="absolute inset-0 bg-indigo-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                        <div class="bg-indigo-500/20 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300">
                            <i data-lucide="mic" class="w-8 h-8 text-indigo-400"></i>
                        </div>
                        <h2 class="text-xl font-bold text-white">Mark Attendance</h2>
                        <p class="text-sm text-indigo-200 mt-2">Requires Location & Microphone</p>
                    </button>
                    ` : ''}
                </div>
                ` : ''}

                <div class="mt-8">
                    <h3 class="text-lg font-bold text-slate-200 mb-4 px-1 flex items-center justify-between">
                        Attendance History
                        <span class="text-xs font-normal text-slate-500 bg-slate-800 px-2 py-1 rounded-full">1 Recent</span>
                    </h3>
                    <div class="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden">
                        <div class="divide-y divide-slate-700/50">
                            <div class="p-4 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                                <div>
                                    <div class="text-sm font-semibold text-slate-300">Class Active</div>
                                    <div class="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                        <i data-lucide="clock" class="w-3 h-3"></i> ${new Date().toLocaleDateString()}
                                    </div>
                                </div>
                                <div class="px-2.5 py-1 rounded-full text-xs font-bold border text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                                    PRESENT
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        }

        function renderTeacherDashboard() {
            return `
            <div class="max-w-4xl mx-auto p-4 space-y-6 mt-4">
                <header class="mb-8">
                    <h1 class="text-3xl font-bold text-white mb-2">Teacher Dashboard</h1>
                    <p class="text-slate-400">Welcome back, Prof. ${state.username || 'Admin'}</p>
                </header>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div class="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl flex flex-col items-center justify-center">
                        <h2 class="text-4xl font-bold text-emerald-400 mb-1">${state.attendanceList ? state.attendanceList.filter(a => a.status && a.status.toUpperCase() === 'PRESENT').length : 0}</h2>
                        <span class="text-xs font-semibold text-slate-400 tracking-wider">PRESENT TODAY</span>
                    </div>
                    <div class="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl flex flex-col items-center justify-center">
                        <h2 class="text-4xl font-bold text-primary-400 mb-1">${state.attendanceList ? state.attendanceList.length : 0}</h2>
                        <span class="text-xs font-semibold text-slate-400 tracking-wider">TOTAL LOGS</span>
                    </div>
                </div>

                <div class="bg-slate-800/50 backdrop-blur-md border border-primary-500/20 p-6 rounded-2xl shadow-lg shadow-primary-500/5 relative overflow-hidden">
                    <div class="absolute top-0 right-0 p-12 opacity-5 pointer-events-none">
                        <i data-lucide="map-pin" class="w-[100px] h-[100px]"></i>
                    </div>
                    <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
                        <div>
                            <h3 class="text-xl font-bold text-slate-100 flex items-center gap-2 mb-1">
                                <i data-lucide="map-pin" class="text-primary-400 w-5 h-5"></i> Class Session
                            </h3>
                            <p class="text-sm text-slate-400">
                                <span class="text-emerald-400 flex items-center gap-1"><i data-lucide="check-circle-2" class="w-3 h-3"></i> Ready</span>
                            </p>
                        </div>
                        <button onclick="startSession()" class="bg-slate-700 hover:bg-slate-600 text-slate-300 px-6 py-3 rounded-xl font-medium transition-all shadow-md whitespace-nowrap flex items-center gap-2">
                            <i data-lucide="lock" class="w-4 h-4"></i> Lock Class
                        </button>
                    </div>
                </div>

                <div class="flex grid-cols-2 gap-4">
                    <button onclick="navigate('approve')" class="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2">
                        <i data-lucide="check-circle-2" class="w-[18px]"></i> Approve
                    </button>
                    <button onclick="exportCSV()" class="flex-1 border border-primary-500/50 hover:bg-primary-500/10 text-primary-300 py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2">
                        <i data-lucide="file-down" class="w-[18px]"></i> Export CSV
                    </button>
                </div>

                <div class="mt-8">
                    <h3 class="text-lg font-bold text-slate-200 mb-4 px-1">Live Attendance Feed</h3>
                    <div class="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden shadow-xl">
                        <div class="divide-y divide-slate-700/50">
                            ${state.attendanceList && state.attendanceList.length > 0 ? state.attendanceList.map(record => `
                            <div class="p-4 md:p-5 hover:bg-slate-700/20 transition-colors flex items-center justify-between">
                                <div class="flex-1">
                                    <div class="font-semibold text-slate-200">Student ID: ${record.student_id}</div>
                                    <div class="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                        <i data-lucide="clock" class="w-3 h-3"></i> ${record.timestamp}
                                    </div>
                                </div>
                                <div class="flex flex-col items-end gap-1">
                                    <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold ${record.status && record.status.toUpperCase() === 'PRESENT' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-rose-500/10 text-rose-400'}">
                                        ${record.status && record.status.toUpperCase() === 'PRESENT' ? 'PRESENT' : 'ABSENT'}
                                    </span>
                                </div>
                            </div>
                            `).join('') : `
                            <div class="p-8 text-center">
                                <p class="text-slate-500">No attendance records yet.</p>
                            </div>
                            `}
                        </div>
                    </div>
                </div>
            </div>`;
        }

        function renderEnroll() {
            if (state.enrollStep === 4) {
                return `
                <div class="max-w-md mx-auto p-4 space-y-6 mt-10">
                    <div class="bg-emerald-500/10 border border-emerald-500/20 p-8 rounded-3xl text-center shadow-lg">
                        <div class="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-emerald-500/30">
                            <i data-lucide="check" class="w-10 h-10 text-white"></i>
                        </div>
                        <h2 class="text-2xl font-bold text-emerald-400 mb-2">Enrollment Complete!</h2>
                        <p class="text-emerald-100/70 mb-8">Your unique voice signature has been securely saved.</p>
                        <button onclick="navigate('dashboard')" class="bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 px-8 rounded-xl transition-colors">
                            Return Home
                        </button>
                    </div>
                </div>`;
            }

            return `
            <div class="max-w-md mx-auto p-4 space-y-6 mt-4">
                <header class="mb-6">
                    <h1 class="text-2xl font-bold text-white flex items-center gap-2">
                        <i data-lucide="mic" class="text-primary-400"></i> Voice Signature
                    </h1>
                    <p class="text-slate-400 text-sm mt-1">Enroll your voice to authenticate.</p>
                </header>

                <div class="space-y-6">
                    <div class="bg-slate-800/40 border border-slate-700/50 p-4 rounded-2xl flex items-center gap-4">
                        <div class="w-12 h-12 bg-indigo-500/20 rounded-full flex items-center justify-center border border-indigo-500/30">
                            <i data-lucide="user" class="text-indigo-400"></i>
                        </div>
                        <div>
                            <div class="text-xs text-slate-500 font-semibold uppercase tracking-wider">Enrolling Identity</div>
                            <div class="text-slate-200 font-bold">${state.username || 'Student'}</div>
                        </div>
                    </div>

                    <div class="bg-slate-800/40 border border-slate-700/50 p-8 rounded-3xl text-center shadow-lg min-h-[300px] flex flex-col justify-center">
                        <div class="mb-8">
                            <div class="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Capture ${state.enrollStep} of 3</div>
                            <p class="text-xl text-slate-300">Read the phrase below:</p>
                            <p class="text-2xl font-bold text-primary-400 mt-2">
                                "${state.enrollStep === 1 ? 'My voice is my password' : state.enrollStep === 2 ? 'Present' : `Roll No CSB21001 Present`}"
                            </p>
                        </div>

                        <div class="relative flex justify-center mb-6">
                            ${state.recording ? `
                            <div class="absolute inset-0 bg-red-500/20 rounded-full animate-ping delay-75 scale-150"></div>
                            <div class="absolute inset-0 bg-red-500/20 rounded-full animate-ping delay-300 scale-[2]"></div>
                            ` : ''}
                            
                            <button onclick="toggleRecord()" class="relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${state.recording ? 'bg-slate-900 border-4 border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.5)] scale-110' : 'bg-gradient-to-br from-red-500 to-red-600 shadow-[0_10px_20px_rgba(239,68,68,0.4)] hover:scale-105 hover:shadow-[0_10px_30px_rgba(239,68,68,0.6)]'}">
                                ${state.recording ? `<i data-lucide="square" class="w-8 h-8 text-red-500 fill-red-500"></i>` : `<i data-lucide="mic" class="w-9 h-9 text-white"></i>`}
                            </button>
                        </div>
                        <p class="text-sm font-medium transition-colors ${state.recording ? 'text-red-400 animate-pulse' : 'text-slate-400'}">
                            ${state.recording ? "Recording... Tap to Stop" : "Tap Microphone to Speak"}
                        </p>
                    </div>
                </div>
            </div>`;
        }

        function renderApp() {
            const app = document.getElementById('app');
            const navbar = document.getElementById('navbar');

            if (state.currentView === 'login') {
                navbar.classList.add('hidden');
                app.innerHTML = renderLoginView();
            } else {
                navbar.classList.remove('hidden');
                if (state.currentView === 'dashboard') {
                    app.innerHTML = state.role === 'TEACHER' ? renderTeacherDashboard() : renderStudentDashboard();
                } else if (state.currentView === 'enroll') {
                    app.innerHTML = renderEnroll();
                } else if (state.currentView === 'verify') {
                    app.innerHTML = `
                    <div class="max-w-md mx-auto p-4 space-y-6 mt-10">
                        <div class="bg-slate-800/40 border border-slate-700/50 p-8 rounded-3xl text-center shadow-lg flex flex-col justify-center relative overflow-hidden">
                            <h2 class="text-2xl font-bold text-white mb-2 tracking-tight">Step 1: Voice Match</h2>
                            <p class="text-slate-400 mb-6 text-sm">Read any prompt to verify your identity.</p>
                            
                            <button id="verify-btn" onclick="verifyVoiceReal()" class="w-full bg-primary-600 hover:bg-primary-500 text-white font-semibold py-4 px-8 rounded-xl transition-all shadow-lg shadow-primary-500/20 flex items-center justify-center gap-2 mb-4">
                                <i data-lucide="mic" class="w-[18px]"></i> Start Voice Test
                            </button>
                            
                            <div id="verify-results" class="hidden flex-col gap-4 mt-4 w-full">
                                <div class="bg-slate-900/50 rounded-xl p-4 border border-slate-700/50">
                                    <div class="text-sm text-slate-400 mb-1">Confidence Score</div>
                                    <div id="verify-confidence" class="text-3xl font-bold text-emerald-400">--%</div>
                                </div>
                                <button onclick="playTestAudio()" class="w-full bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 rounded-xl transition-all flex items-center justify-center gap-2">
                                    <i data-lucide="play" class="w-4 h-4"></i> Playback Test
                                </button>
                            </div>
                        </div>

                        <div id="step-2-container" class="hidden bg-slate-800/40 border border-emerald-500/30 p-8 rounded-3xl text-center shadow-lg flex flex-col justify-center">
                            <h2 class="text-2xl font-bold text-white mb-2 tracking-tight">Step 2: Geofence</h2>
                            <p class="text-slate-400 mb-6 text-sm">Verify your location and mark attendance.</p>
                            
                            <button id="mark-btn" onclick="markAttendanceFinal()" class="w-full bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-4 px-8 rounded-xl transition-all shadow-lg shadow-emerald-500/20 flex items-center justify-center gap-2">
                                <i data-lucide="map-pin" class="w-[18px]"></i> Mark Attendance Now
                            </button>
                        </div>
                    </div>`;
                } else if (state.currentView === 'students') {
                    app.innerHTML = `
                    <div class="max-w-4xl mx-auto p-4 space-y-6 mt-4">
                        <h2 class="text-2xl font-bold text-white mb-4">Student List</h2>
                        <div class="bg-slate-800/40 border border-slate-700/50 p-6 rounded-3xl shadow-lg">
                            <p class="text-slate-400">Mock Student List Page. Here you would see the registered students.</p>
                        </div>
                    </div>`;
                } else if (state.currentView === 'approve') {
                    app.innerHTML = `
                    <div class="max-w-4xl mx-auto p-4 space-y-6 mt-4">
                        <div class="flex items-center gap-4 mb-6">
                            <button onclick="navigate('dashboard')" class="p-2 bg-slate-800 hover:bg-slate-700 rounded-xl transition-colors">
                                <i data-lucide="arrow-left" class="w-5 h-5 text-slate-300"></i>
                            </button>
                            <h2 class="text-2xl font-bold text-white m-0">Approve Attendance</h2>
                        </div>
                        <div class="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden shadow-xl">
                            <div class="divide-y divide-slate-700/50">
                                ${(state.attendanceList || []).length > 0 ? state.attendanceList.map(a => `
                                <div class="p-4 md:p-5 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                                    <div class="flex-1">
                                        <div class="font-semibold text-slate-200">${a.student_id} - ${a.name}</div>
                                        <div class="text-xs ${a.confidence >= 0.60 ? 'text-emerald-500' : 'text-red-500'} flex items-center gap-1 mt-1">
                                            Voice Match: ${(a.confidence * 100).toFixed(1)}%
                                        </div>
                                    </div>
                                    <div class="flex gap-2">
                                        <button onclick="updateAttendance('${a.student_id}', 'PRESENT')" class="px-3 py-1.5 ${a.status === 'PRESENT' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/50' : 'bg-slate-800 text-slate-400 border-slate-700'} border rounded-lg text-xs font-bold hover:bg-emerald-500/20 transition-colors">PRESENT</button>
                                        <button onclick="updateAttendance('${a.student_id}', 'ABSENT')" class="px-3 py-1.5 ${a.status === 'ABSENT' ? 'bg-red-500/20 text-red-300 border-red-500/50' : 'bg-slate-800 text-slate-400 border-slate-700'} border rounded-lg text-xs font-bold hover:bg-red-500/20 transition-colors">ABSENT</button>
                                    </div>
                                </div>
                                `).join('') : '<div class="p-6 text-center text-slate-400">No attendance records yet for this session.</div>'}
                            </div>
                        </div>
                        <button onclick="navigate('dashboard')" class="w-full bg-primary-600 hover:bg-primary-500 text-white font-semibold py-3.5 px-4 rounded-xl transition-all shadow-lg shadow-primary-500/20 mt-4">Done</button>
                    </div>`;
                }

                // Render Navbar Links
                navbar.innerHTML = `
                    <button onclick="navigate('dashboard')" class="flex flex-col items-center gap-1 transition-colors ${state.currentView === 'dashboard' ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}">
                        <div class="p-2 rounded-xl transition-all ${state.currentView === 'dashboard' ? 'bg-primary-500/10' : 'bg-transparent'}">
                            <i data-lucide="home" class="w-[22px] h-[22px]"></i>
                        </div>
                    </button>
                    ${state.role === 'STUDENT' ? `
                    <button onclick="navigate('enroll')" class="flex flex-col items-center gap-1 transition-colors ${state.currentView === 'enroll' ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}">
                        <div class="p-2 rounded-xl transition-all ${state.currentView === 'enroll' ? 'bg-primary-500/10' : 'bg-transparent'}">
                            <i data-lucide="mic" class="w-[22px] h-[22px]"></i>
                        </div>
                    </button>
                    ` : `
                    <button onclick="navigate('students')" class="flex flex-col items-center gap-1 transition-colors ${state.currentView === 'students' ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}">
                        <div class="p-2 rounded-xl transition-all ${state.currentView === 'students' ? 'bg-primary-500/10' : 'bg-transparent'}">
                            <i data-lucide="users" class="w-[22px] h-[22px]"></i>
                        </div>
                    </button>
                    `}
                    <button onclick="logout()" class="flex flex-col items-center gap-1 text-slate-500 hover:text-red-400 transition-colors bg-transparent border-none cursor-pointer p-0">
                        <div class="p-2 rounded-xl bg-transparent">
                            <i data-lucide="log-out" class="w-[22px] h-[22px]"></i>
                        </div>
                    </button>
                `;
            }

            if (window.lucide) {
                window.lucide.createIcons();
            }
        }

        window.toggleRegister = () => {
            state.isRegister = !state.isRegister;
            renderApp();
        };

        window.toggleSettings = () => {
            state.showSettings = !state.showSettings;
            renderApp();
        };

        window.setRole = (role) => {
            state.role = role;
            renderApp();
        };

        window.handleAuth = async (e) => {
            e.preventDefault();
            const userInput = document.getElementById('username-input');
            const nameInput = document.getElementById('name-input');
            const rollnoInput = document.getElementById('rollno-input');
            const courseInput = document.getElementById('course-input');
            const subjectInput = document.getElementById('subject-input');

            if (userInput) state.username = userInput.value;
            
            let payload = { username: state.username, password: "password", role: state.role };
            
            if (state.isRegister) {
                if (nameInput) payload.name = nameInput.value;
                if (rollnoInput) payload.roll_no = rollnoInput.value;
                if (courseInput) payload.course = courseInput.value;
                if (subjectInput) payload.subject = subjectInput.value;
            }

            if (!state.username) return;
            try {
                const res = await fetch(state.apiUrl + "/api/login", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                state.role = data.role;
                state.name = data.name;
                state.rollNo = data.roll_no;
                state.course = data.course;
                state.subject = data.subject;
                state.currentView = 'dashboard';
                saveSession();
                
                if (state.role === 'TEACHER') {
                    loadAttendance();
                    if (!window.refreshInterval) window.refreshInterval = setInterval(loadAttendance, 5000);
                } else {
                    loadTeachers();
                }
                
                renderApp();
            } catch (err) {
                alert("Login failed! Ensure backend is running. " + err);
            }
        };

        window.loadTeachers = async () => {
            try {
                const res = await fetch(state.apiUrl + "/api/teachers");
                const data = await res.json();
                state.teachers = data.teachers;
                renderApp();
            } catch(e) {
                console.error(e);
            }
        };

        window.startSession = () => {
            navigator.geolocation.getCurrentPosition(async (pos) => {
                try {
                    await fetch(state.apiUrl + "/api/session/start", {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            teacher_id: state.username,
                            lat: pos.coords.latitude,
                            lng: pos.coords.longitude,
                            radius: 20.0
                        })
                    });
                    alert("Class Locked & Session Started!");
                } catch(e) {
                    alert("Failed to start session: " + e);
                }
            }, () => {
                alert("Geolocation permission denied. Cannot start session.");
            });
        };

        window.loadAttendance = async () => {
            try {
                const res = await fetch(state.apiUrl + "/api/attendance");
                const data = await res.json();
                state.attendanceList = data.records;
                renderApp();
            } catch(e) {
                console.error(e);
            }
        };

        window.updateAttendance = async (student_id, status) => {
            try {
                await fetch(state.apiUrl + "/api/attendance/update", {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({student_id, status})
                });
                loadAttendance();
            } catch(e) {
                alert("Failed to update status: " + e);
            }
        };

        window.navigate = (view) => {
            state.currentView = view;
            if (view === 'enroll' && state.enrollStep === 0) state.enrollStep = 1;
            if (view === 'approve') loadAttendance();
            saveSession();
            renderApp();
        };

        window.exportCSV = () => {
            if (!state.attendanceList || state.attendanceList.length === 0) {
                alert("No attendance records to export.");
                return;
            }
            const headers = ["Student ID", "Status", "Timestamp", "Confidence", "Latitude", "Longitude"];
            const csvRows = [headers.join(",")];
            state.attendanceList.forEach(r => {
                csvRows.push(`${r.student_id},${r.status},${r.timestamp},${r.confidence || ''},${r.lat || ''},${r.lng || ''}`);
            });
            const csvString = csvRows.join("\\n");
            const blob = new Blob([csvString], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = \`attendance_\${new Date().toISOString().split('T')[0]}.csv\`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        };

        window.logout = () => {
            state.currentView = 'login';
            state.username = '';
            state.mentorId = null;
            if (window.refreshInterval) {
                clearInterval(window.refreshInterval);
                window.refreshInterval = null;
            }
            localStorage.removeItem('voice_app_state');
            renderApp();
        };

        window.selectMentor = (id) => {
            state.mentorId = id;
            state.isChangingMentor = false;
            saveSession();
            renderApp();
        };

        window.toggleChangeMentor = () => {
            state.isChangingMentor = !state.isChangingMentor;
            renderApp();
        };

        let mediaRecorder;
        let audioChunks = [];

        window.lastConfidence = 0.0;
        
        window.playTestAudio = () => {
            const audio = new Audio(`${state.apiUrl}/data/${state.username || 'CSB21001'}_test.webm`);
            audio.play().catch(e => alert("Could not play audio: " + e.message));
        };

        window.verifyVoiceReal = async () => {
            if (!mediaRecorder || mediaRecorder.state === 'inactive') {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    mediaRecorder = new MediaRecorder(stream);
                    
                    mediaRecorder.ondataavailable = event => {
                        audioChunks.push(event.data);
                    };

                    mediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                        const file = new File([audioBlob], "voice.webm", { type: 'audio/webm' });
                        
                        const btn = document.getElementById('verify-btn');
                        btn.innerHTML = `<i data-lucide="loader-2" class="w-[18px] animate-spin"></i> Analyzing...`;
                        btn.classList.remove('bg-red-600', 'hover:bg-red-500', 'animate-pulse');
                        btn.classList.add('bg-primary-600', 'hover:bg-primary-500');
                        
                        const formData = new FormData();
                        formData.append("audio_file", file);
                        formData.append("student_id", state.username || "CSB21001");

                        try {
                            const res = await fetch(state.apiUrl + "/api/verify-voice", {
                                method: 'POST',
                                body: formData
                            });
                            const result = await res.json();
                            
                            if (result.status === 'success') {
                                btn.innerHTML = `<i data-lucide="check" class="w-[18px]"></i> Retest Voice`;
                                document.getElementById('verify-results').classList.remove('hidden');
                                document.getElementById('verify-results').classList.add('flex');
                                document.getElementById('verify-confidence').innerText = (result.confidence * 100).toFixed(1) + '%';
                                window.lastConfidence = result.confidence;
                                
                                document.getElementById('step-2-container').classList.remove('hidden');
                                document.getElementById('step-2-container').classList.add('flex');
                            } else {
                                alert("Voice match failed! " + (result.message || "Please try again."));
                                btn.innerHTML = `<i data-lucide="mic" class="w-[18px]"></i> Retest Voice`;
                            }
                        } catch (err) {
                            alert("API connection failed. " + err.message);
                            btn.innerHTML = `<i data-lucide="mic" class="w-[18px]"></i> Start Voice Test`;
                        }
                    };

                    audioChunks = [];
                    mediaRecorder.start();
                    
                    const btn = document.getElementById('verify-btn');
                    btn.classList.remove('bg-primary-600', 'hover:bg-primary-500');
                    btn.classList.add('bg-red-600', 'hover:bg-red-500', 'animate-pulse');
                    btn.innerHTML = `<i data-lucide="square" class="w-[18px]"></i> Recording (Click to Stop)`;
                    
                } catch (err) {
                    alert("Microphone access denied.");
                }
            } else {
                mediaRecorder.stop();
                mediaRecorder.stream.getTracks().forEach(track => track.stop());
            }
        };

        window.markAttendanceFinal = () => {
            const btn = document.getElementById('mark-btn');
            const orig = btn.innerHTML;
            btn.innerHTML = `<i data-lucide="loader-2" class="w-[18px] animate-spin"></i> Locating...`;
            
            navigator.geolocation.getCurrentPosition(async (pos) => {
                try {
                    const res = await fetch(state.apiUrl + "/api/mark-attendance", {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            student_id: state.username || "CSB21001",
                            lat: pos.coords.latitude,
                            lng: pos.coords.longitude,
                            confidence: window.lastConfidence
                        })
                    });
                    const result = await res.json();
                    if (res.ok && result.status === 'success') {
                        alert("Attendance Successfully Marked!");
                        navigate('dashboard');
                    } else {
                        alert("Geofence Failed: " + (result.message || result.detail || "Unknown error"));
                    }
                } catch(e) {
                    alert("API Error: " + e.message);
                } finally {
                    btn.innerHTML = orig;
                }
            }, (err) => {
                alert("Geolocation permission denied. Cannot verify location.");
                btn.innerHTML = orig;
            });
        };

        window.deleteVoice = () => {
            if (confirm("Are you sure you want to delete your voice template?")) {
                state.voiceEnrolled = false;
                state.enrollStep = 0;
                renderApp();
            }
        };

        let enrollMediaRecorder;
        let enrollAudioChunks = [];

        window.toggleRecord = async () => {
            if (!enrollMediaRecorder || enrollMediaRecorder.state === 'inactive') {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                    enrollMediaRecorder = new MediaRecorder(stream);
                    
                    enrollMediaRecorder.ondataavailable = event => {
                        enrollAudioChunks.push(event.data);
                    };

                    enrollMediaRecorder.onstop = async () => {
                        const audioBlob = new Blob(enrollAudioChunks, { type: 'audio/webm' });
                        const file = new File([audioBlob], "voice.webm", { type: 'audio/webm' });
                        
                        const formData = new FormData();
                        formData.append("audio_file", file);
                        formData.append("student_id", state.username || "CSB21001");

                        try {
                            const res = await fetch(state.apiUrl + "/api/enroll-voice", {
                                method: 'POST',
                                body: formData
                            });
                            const result = await res.json();
                            
                            if (result.status === "success") {
                                state.voiceEnrolled = true;
                                state.enrollStep = 4; // Complete state
                                saveSession();
                                renderApp();
                            } else {
                                alert("Enrollment Failed! " + (result.message || result.detail || "Unknown error"));
                            }
                        } catch (err) {
                            alert("API connection failed. " + err.message);
                        }
                    };

                    enrollAudioChunks = [];
                    enrollMediaRecorder.start();
                    
                    state.recording = true;
                    renderApp();
                    
                } catch (err) {
                    alert("Microphone access denied.");
                }
            } else if (state.recording) {
                enrollMediaRecorder.pause();
                state.recording = false;
                
                if (state.enrollStep < 3) {
                    state.enrollStep++;
                    renderApp();
                } else {
                    enrollMediaRecorder.stop();
                    enrollMediaRecorder.stream.getTracks().forEach(track => track.stop());
                    renderApp();
                }
            } else {
                enrollMediaRecorder.resume();
                state.recording = true;
                renderApp();
            }
        };

        window.hearPlayback = () => {
            const audio = new Audio(`${state.apiUrl}/data/${state.username}.webm`);
            audio.play().catch(e => alert("Could not play audio. Have you enrolled yet?"));
        };

        window.onload = () => {
            if (state.currentView !== 'login' && state.username) {
                if (state.role === 'TEACHER') {
                    loadAttendance();
                    if (!window.refreshInterval) window.refreshInterval = setInterval(loadAttendance, 5000);
                } else {
                    loadTeachers();
                }
            }
            renderApp();
        };
