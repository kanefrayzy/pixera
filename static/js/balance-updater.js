/**
 * Real-time Balance Updater
 * Обновляет баланс пользователя в реальном времени после генерации
 */

(function() {
  'use strict';

  // Функция для обновления баланса в UI
  function updateBalanceDisplay(newBalance) {
    try {
      // Для авторизованных пользователей
      const balanceEl = document.getElementById('balance');
      if (balanceEl && !balanceEl.dataset.infinite) {
        const currentBalance = parseInt(balanceEl.textContent) || 0;
        const targetBalance = parseInt(newBalance) || 0;

        // Анимированное обновление
        animateBalanceChange(balanceEl, currentBalance, targetBalance);
      }

      // Для гостей
      const guestBalanceEl = document.getElementById('guestBalance');
      if (guestBalanceEl) {
        const currentBalance = parseInt(guestBalanceEl.textContent) || 0;
        const targetBalance = parseInt(newBalance) || 0;

        animateBalanceChange(guestBalanceEl, currentBalance, targetBalance);
      }

      console.log('[Balance] Updated to:', newBalance);
    } catch (e) {
      console.error('[Balance] Error updating display:', e);
    }
  }

  // Анимация изменения баланса
  function animateBalanceChange(element, from, to) {
    if (!element) return;

    const duration = 500; // 0.5 секунды
    const steps = 20;
    const stepDuration = duration / steps;
    const diff = to - from;
    const stepValue = diff / steps;

    let currentStep = 0;

    const interval = setInterval(() => {
      currentStep++;
      const newValue = Math.round(from + (stepValue * currentStep));

      element.textContent = newValue;

      // Добавляем визуальный эффект
      if (diff < 0) {
        element.classList.add('text-red-500');
        setTimeout(() => element.classList.remove('text-red-500'), 300);
      }

      if (currentStep >= steps) {
        clearInterval(interval);
        element.textContent = to;
      }
    }, stepDuration);
  }

  // Функция для получения актуального баланса с сервера
  async function fetchCurrentBalance() {
    try {
      const response = await fetch('/dashboard/api/wallet/info/', {
        method: 'GET',
        headers: {
          'X-Requested-With': 'fetch',
          'Accept': 'application/json'
        },
        credentials: 'same-origin'
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      if (data.ok && data.balance !== undefined) {
        updateBalanceDisplay(data.balance);
        return data.balance;
      }
    } catch (e) {
      console.error('[Balance] Error fetching balance:', e);
    }
    return null;
  }

  // Функция для уменьшения баланса локально (оптимистичное обновление)
  function decreaseBalance(cost) {
    try {
      const balanceEl = document.getElementById('balance');
      const guestBalanceEl = document.getElementById('guestBalance');

      const element = balanceEl && !balanceEl.dataset.infinite ? balanceEl : guestBalanceEl;

      if (element) {
        const currentBalance = parseInt(element.textContent) || 0;
        const newBalance = Math.max(0, currentBalance - cost);
        updateBalanceDisplay(newBalance);
      }
    } catch (e) {
      console.error('[Balance] Error decreasing balance:', e);
    }
  }

  // Экспортируем функции глобально
  window.balanceUpdater = {
    update: updateBalanceDisplay,
    fetch: fetchCurrentBalance,
    decrease: decreaseBalance
  };

  // Автоматически обновляем баланс при загрузке страницы
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      // Небольшая задержка для корректной инициализации
      setTimeout(fetchCurrentBalance, 500);
    });
  } else {
    setTimeout(fetchCurrentBalance, 500);
  }

  console.log('[Balance] Balance updater initialized');
})();
