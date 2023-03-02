import uuid
from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from starlette import status

from app.models import Stream, User, AuthToken, StreamStatus, connect_db
from app.forms import UserCreateForm, UserLoginForm, StreamForm, StreamUpdateForm
from app.authentication import check_auth_token
from app.utils import get_password_hash
from app.exceptions import PerevalExistsException

router = APIRouter()


@router.post('/login', name='user:login')
def login(user_form: UserLoginForm = Body(..., embed=True), database=Depends(connect_db)):
    user = database.query(User).filter(User.email == user_form.email).one_or_none()
    if not user or get_password_hash(user_form.password) != user.password:
        return {'error': 'Email/password doesnt match'}

    auth_model = AuthToken(token=str(uuid.uuid4()), user_id=user.id, created_at=datetime.now())
    database.add(auth_model)
    database.commit()
    return {'auth_token': auth_model.token}


@router.get('/user', name='user:get')
def get_pereval(database: str, id: int):
    # получаем данные о перевале
    pereval = database.query(Added).filter(Added.id == id).first()
    if not pereval:
        raise PerevalExistsException(id=id)
    # получаем данные о пользователе
    user = database.query(Users).filter(Users.id == pereval.user_id).first()
    # получаем данные о координатах
    coords = database.query(Coords).filter(Coords.id == pereval.coords_id).first()
    # получаем данные об уровнях
    level = database.query(Level).filter(Level.id == pereval.level_id).first()
    result = jsonable_encoder(pereval)
    result['user'] = jsonable_encoder(user)
    result['coords'] = jsonable_encoder(coords)
    result['level'] = jsonable_encoder(level)
    return result
# получить данные о перевалах по почте user
def get_pereval_by_user_email(database: str, email: str):
    # получить данные о пользователе
    get_user = database.query(Users).filter(Users.email == email).first()
    # получить перевалы
    get_all_pereval = database.query(Added).filter(Added.user_id == get_user.id).all()
    # добавляем в список все полученные перевалы
    list = [jsonable_encoder(pereval) for pereval in get_all_pereval]
    pereval = {"pereval": list}
    return pereval
def get_user(token: AuthToken = Depends(check_auth_token), database=Depends(connect_db)):
    user = database.query(User).filter(User.id == token.user_id).one_or_none()
    return {'user': user.get_filtered_data()}
def get_user_by_email(database: str, email: str):
    return database.query(Users).filter(Users.email == email).first()

@router.post('/user', name='user:create')
def create_user(user: UserCreateForm = Body(..., embed=True), database=Depends(connect_db)):
    exists_user = database.query(User.id).filter(User.email == user.email).one_or_none()
    if exists_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already taken',
        )

    new_user = User(
        email=user.email,
        password=get_password_hash(user.password),
        first_name=user.first_name,
        last_name=user.last_name,
        nickname=user.nickname
    )
    database.add(new_user)
    database.commit()
    return {'user_id': new_user.id}


@router.get('/stream', name='stream:get')
def get_stream(token: AuthToken = Depends(check_auth_token), database=Depends(connect_db)):
    streams_list = database.query(Stream).filter(Stream.user_id == token.user_id).all()
    return streams_list


@router.post('/stream', name='stream:create')
def create_stream(
        token: AuthToken = Depends(check_auth_token),
        stream_form: StreamForm = Body(..., embed=True),
        database=Depends(connect_db)
):
    stream = Stream(user_id=token.user_id, title=stream_form.title, topic=stream_form.topic, description=stream_form.description)
    database.add(stream)
    database.commit()
    return {'status': 'created'}


@router.put('/stream', name='stream:update')
def update_stream(
        token: AuthToken = Depends(check_auth_token),
        stream_form: StreamUpdateForm = Body(..., embed=True),
        database=Depends(connect_db)
):
    """
    Change stream status: active or closed
    """
    if stream_form.status not in (StreamStatus.ACTIVE.value, StreamStatus.CLOSED.value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Status must be active or closed',
        )

    stream = database.query(Stream).filter(Stream.id == stream_form.stream_id, Stream.user_id == token.user_id).one_or_none()
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f'Stream with id {stream_form.stream_id} doesnt exist',
        )

    stream.status = stream_form.status
    database.add(stream)
    database.commit()
    return {'status': stream_form.status}
