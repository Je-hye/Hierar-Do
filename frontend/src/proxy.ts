import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

// 보호할 라우트 패턴 (정규식 또는 정확한 경로)
const protectedRoutes = ['/', '/calendar', '/settings'];
const authRoutes = ['/login', '/register'];

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;
  
  // accessToken 확인 (HttpOnly 쿠키 이름이 access_token 인 경우)
  const hasToken = request.cookies.has('access_token');

  // 보호된 라우트에 접근하려는데 토큰이 없는 경우 -> 로그인으로 리다이렉트
  if (!hasToken && protectedRoutes.some(route => pathname === route || pathname.startsWith(route + '/'))) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // 로그인/회원가입 라우트에 접근하려는데 토큰이 이미 있는 경우 -> 대시보드로 리다이렉트
  if (hasToken && authRoutes.includes(pathname)) {
    return NextResponse.redirect(new URL('/', request.url));
  }

  return NextResponse.next();
}

// 미들웨어가 실행될 경로 지정 (Next.js 권장 설정)
export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};
