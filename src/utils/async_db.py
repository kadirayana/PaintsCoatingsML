"""
Async Database Wrapper
======================
UI thread'ini bloklamadan veritabanı işlemleri için wrapper.

Kullanım:
    from src.utils.async_db import run_async, AsyncDBOperation, run_on_main_thread
    
    # Basit kullanım
    run_async(
        db_manager.get_all_projects,
        callback=lambda data: update_ui(data),
        error_callback=lambda e: show_error(str(e))
    )
    
    # Fluent interface
    AsyncDBOperation(db_manager.get_project_hierarchy)\\
        .on_success(lambda data: run_on_main_thread(root, update_sidebar, data))\\
        .on_error(lambda e: logger.error(e))\\
        .execute()
"""
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Any, Optional
import threading

logger = logging.getLogger(__name__)

# Global thread pool - tüm DB işlemleri için paylaşılır
_executor: Optional[ThreadPoolExecutor] = None
_lock = threading.Lock()


def get_executor() -> ThreadPoolExecutor:
    """Thread pool singleton"""
    global _executor
    if _executor is None:
        with _lock:
            if _executor is None:
                _executor = ThreadPoolExecutor(
                    max_workers=3,
                    thread_name_prefix="db_worker"
                )
    return _executor


def shutdown_executor():
    """Thread pool'u kapat (uygulama kapanırken çağrılmalı)"""
    global _executor
    if _executor is not None:
        _executor.shutdown(wait=False)
        _executor = None


def run_async(func: Callable, *args, callback: Callable = None, 
              error_callback: Callable = None, **kwargs) -> None:
    """
    Veritabanı işlemini arka planda çalıştır.
    
    Args:
        func: Çalıştırılacak fonksiyon
        *args: Fonksiyon argümanları
        callback: Başarılı sonuç callback'i (result) -> None
        error_callback: Hata callback'i (exception) -> None
        **kwargs: Fonksiyon keyword argümanları
    
    Usage:
        def on_result(projects):
            update_ui(projects)
        
        def on_error(e):
            show_error(str(e))
        
        run_async(
            db_manager.get_all_projects,
            callback=on_result,
            error_callback=on_error
        )
    """
    def wrapper():
        try:
            result = func(*args, **kwargs)
            if callback:
                callback(result)
        except Exception as e:
            logger.error(f"Async DB operation failed: {e}")
            if error_callback:
                error_callback(e)
    
    get_executor().submit(wrapper)


class AsyncDBOperation:
    """
    Context manager style async DB wrapper.
    
    Usage:
        async_op = AsyncDBOperation(db_manager.get_project_hierarchy)
        async_op.on_success(lambda data: update_sidebar(data))
        async_op.on_error(lambda e: show_error(e))
        async_op.execute()
    
    Fluent style:
        AsyncDBOperation(db_manager.get_all_materials)\\
            .on_success(update_material_list)\\
            .on_error(log_error)\\
            .execute()
    """
    
    def __init__(self, func: Callable, *args, **kwargs):
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._success_callback = None
        self._error_callback = None
    
    def on_success(self, callback: Callable) -> 'AsyncDBOperation':
        """Başarı callback'i ayarla (fluent interface)"""
        self._success_callback = callback
        return self
    
    def on_error(self, callback: Callable) -> 'AsyncDBOperation':
        """Hata callback'i ayarla (fluent interface)"""
        self._error_callback = callback
        return self
    
    def execute(self) -> None:
        """İşlemi başlat"""
        run_async(
            self._func, 
            *self._args,
            callback=self._success_callback,
            error_callback=self._error_callback,
            **self._kwargs
        )


def run_on_main_thread(root, callback: Callable, *args) -> None:
    """
    Callback'i Tkinter main thread'inde çalıştır.
    
    Bu fonksiyon, arka plan thread'inden UI güncellemesi yapmak için
    Tkinter'ın after() metodunu kullanır.
    
    Args:
        root: Tkinter root window
        callback: Çalıştırılacak fonksiyon
        *args: Fonksiyon argümanları
    
    Usage:
        # Arka plan thread'inden UI güncelleme
        run_on_main_thread(self.root, self._update_project_list, projects)
    """
    root.after(0, lambda: callback(*args))


def run_on_main_thread_with_kwargs(root, callback: Callable, *args, **kwargs) -> None:
    """
    Callback'i Tkinter main thread'inde kwargs ile çalıştır.
    
    Args:
        root: Tkinter root window
        callback: Çalıştırılacak fonksiyon
        *args: Fonksiyon argümanları
        **kwargs: Fonksiyon keyword argümanları
    """
    root.after(0, lambda: callback(*args, **kwargs))
