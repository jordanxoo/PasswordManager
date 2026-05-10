from fastapi import APIRouter, Depends, HTTPException                                    
from sqlalchemy.ext.asyncio import AsyncSession                                          
from sqlalchemy import select                                                            
from app.database import get_db                                                          
from app.models.models import User                                                       
from app.models.enums import Role                                                        
from app.schemas.user import UserResponse, UpdateRoleRequest, UpdateBlockRequest
from app.dependencies import require_admin                                               
from app.publishers.security_publisher import publish_security_alert
                                            
router = APIRouter()                                                                     

                                                                                        
@router.get("/users", response_model=list[UserResponse])
async def get_users(db: AsyncSession = Depends(get_db),                                  
                    admin_id: str = Depends(require_admin)):
    result = await db.execute(select(User)) 
    users = result.scalars().all()      
    return list(users)
                                                                                        
                                            
@router.get("/users/{user_id}", response_model=UserResponse)                             
async def get_user(user_id: str,
                    db: AsyncSession = Depends(get_db),                                   
                    admin_id: str = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))                    
    user = result.scalar_one_or_none()  

    if user is None:                                                                     
        raise HTTPException(status_code=404, detail="User not found")
                                                                                        
    return user                         

                                                                                        
@router.put("/users/{user_id}/role", response_model=UserResponse)
async def update_role(user_id: str,                                                      
                    data: UpdateRoleRequest,
                    db: AsyncSession = Depends(get_db),
                    admin_id: str = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
                                                                                        
    if user is None:                    
        raise HTTPException(status_code=404, detail="User not found")                    
                                                                                        
    user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user


@router.put("/users/{user_id}/block", response_model=UserResponse)
async def update_block(user_id: str,
                        data: UpdateBlockRequest,
                        db: AsyncSession = Depends(get_db),
                        admin_id: str = Depends(require_admin)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_blocked = data.is_blocked
    await db.commit()
    await db.refresh(user)

    if data.is_blocked:
        await publish_security_alert("account_blocked_by_admin", user.email,
                                    "admin_action", admin_id)

    return user
