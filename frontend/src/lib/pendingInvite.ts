/**
 * A pending invite token, stashed across the login/register round-trip so an
 * unauthenticated invitee can sign in (or sign up) and land back on the invite.
 */
const KEY = "pendingInviteToken";

export const setPendingInvite = (token: string) => sessionStorage.setItem(KEY, token);
export const getPendingInvite = () => sessionStorage.getItem(KEY);
export const clearPendingInvite = () => sessionStorage.removeItem(KEY);

/** Where to go after a successful login: back to a pending invite, else home. */
export const postAuthPath = () => (getPendingInvite() ? "/invite" : "/");
