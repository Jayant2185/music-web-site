from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.http import HttpResponse
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.db.models import Q
from .forms import AlbumForm, SongForm, UserForm
from .models import Album, Song
from django.views import generic
from .utils import logger
from .dblog import log

AUDIO_FILE_TYPES = ['wav', 'mp3', 'ogg']
IMAGE_FILE_TYPES = ['png', 'jpg', 'jpeg']

def index(request):
    albums = Album.objects.filter(user=request.user)
    song_results = Song.objects.all()
    query = request.GET.get("q")
    if query:
        albums = albums.filter(
                Q(album_title__icontains=query) |
                Q(artist__icontains=query)
            ).distinct()
        song_results = song_results.filter(
                Q(song_title__icontains=query)
            ).distinct()
        logger.info("Index with album and songs")

        return render(request, 'music/index.html', {
                'albums': albums,
                'songs': song_results,
            })
    else:
        logger.info("Index with albums")
        return render(request, 'music/index.html', {'albums': albums})


class DetailView(generic.DetailView):
    model=Album
    template_name='music/detail.html'
    logger.info("Details of Songs")

def create_album(request):
    form = AlbumForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        album = form.save(commit=False)
        album.user = request.user
        album.album_logo = request.FILES['album_logo']
        file_type = album.album_logo.url.split('.')[-1]
        file_type = file_type.lower()
        if file_type not in IMAGE_FILE_TYPES:
            context = {
                    'album': album,
                    'form': form,
                    'error_message': 'Image file must be PNG, JPG, or JPEG',
                }
            logger.warning("upload picture error")
            return render(request, 'music/create_album.html', context)
        album.save()
        logger.info("New Albam Created")
        return render(request, 'music/detail.html', {'album': album})
    context = {
            "form": form,
        }
    logger.info("Albam called")
    return render(request, 'music/create_album.html', context)


def create_song(request, album_id):
    form = SongForm(request.POST or None, request.FILES or None)
    album = get_object_or_404(Album, pk=album_id)
    if form.is_valid():
        albums_songs = album.song_set.all()
        for s in albums_songs:
            if s.song_title == form.cleaned_data.get("song_title"):
                context = {
                    'album': album,
                    'form': form,
                    'error_message': 'You already added that song',
                }
                logger.warning("Duplicate Song")
                return render(request, 'music/create_song.html', context)
        song = form.save(commit=False)
        song.album = album
        song.audio_file = request.FILES['audio_file']
        file_type = song.audio_file.url.split('.')[-1]
        file_type = file_type.lower()
        if file_type not in AUDIO_FILE_TYPES:
            context = {
                'album': album,
                'form': form,
                'error_message': 'Audio file must be WAV, MP3, or OGG',
            }
            logger.warning("Not Audio file")
            return render(request, 'music/create_song.html', context)
        song.save()
        logger.info("Song Added")
        #log.info("Song Added")
        return render(request, 'music/detail.html', {'album': album})
    context = {
        'album': album,
        'form': form,
    }
    logger.info("add song page called")
    return render(request, 'music/create_song.html', context)

def delete_album(request, album_id):
    album = Album.objects.get(pk=album_id)
    album.delete()
    albums = Album.objects.filter(user=request.user)
    logger.info("Album Deleted")
    return render(request, 'music/index.html', {'albums': albums})


def delete_song(request, album_id, song_id):
    album = get_object_or_404(Album, pk=album_id)
    song = Song.objects.get(pk=song_id)
    song.delete()
    logger.info("Song Deleted")
    return render(request, 'music/detail.html', {'album': album})


def favorite(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    try:
        if song.is_favorite:
            song.is_favorite = False
        else:
            song.is_favorite = True
        song.save()
    except (KeyError, Song.DoesNotExist):
        logger.info("No Such song")
        return JsonResponse({'success': False})
    else:
        logger.info("Song is Deleted",song_id)
        return JsonResponse({'success': True})


def favorite_album(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
    try:
        if album.is_favorite:
            album.is_favorite = False
        else:
            album.is_favorite = True
        album.save()
        logger.info("Favourite song marked")
    except (KeyError, Album.DoesNotExist):
        logger.info("Not able to mark favourite song")
        return JsonResponse({'success': False})
    else:
        logger.info("Favourite song marked")
        return JsonResponse({'success': True})


def logout_user(request):
    logout(request)
    form = UserForm(request.POST or None)
    context = {
        "form": form,
    }
    logger.info("User logged out")
    return render(request, 'music/login.html', context)


def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                albums = Album.objects.filter(user=request.user)
                logger.info("User logged in",user)
                return render(request, 'music/index.html', {'albums': albums})
            else:
                logger.info("user not able to login",username)
                return render(request, 'music/login.html', {'error_message': 'Your account has been disabled'})
        else:
            logger.info("Invalid User",username)
            return render(request, 'music/login.html', {'error_message': 'Invalid login'})
    return render(request, 'music/login.html')


def register(request):
    form = UserForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        logger.info("New user registered")
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                albums = Album.objects.filter(user=request.user)
                return render(request, 'music/index.html', {'albums': albums})
    context = {
        "form": form,
    }
    return render(request, 'music/register.html', context)


def songs(request, filter_by):
    try:
        song_ids = []
        for album in Album.objects.filter(user=request.user):
            for song in album.song_set.all():
                song_ids.append(song.pk)
        users_songs = Song.objects.filter(pk__in=song_ids)
        if filter_by == 'favorites':
        	users_songs = users_songs.filter(is_favorite=True)
    except Album.DoesNotExist:
        users_songs = []
        logger.info("Favourite song filtered")

    return render(request, 'music/songs.html', {
            'song_list': users_songs,
            'filter_by': filter_by,
        })

