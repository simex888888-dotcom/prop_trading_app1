import { useEffect, useState } from "react";

export function useTelegram() {
  const [tg, setTg] = useState(null);
  const [user, setUser] = useState(null);
  const [initData, setInitData] = useState("");
  const [colorScheme, setColorScheme] = useState("dark");
  const [isReady, setIsReady] = useState(false);

  useEffect(() => {
    const webApp = window.Telegram?.WebApp;

    if (!webApp) {
      // Dev mode без Telegram
      setIsReady(true);
      setColorScheme("dark");
      setInitData("dev_mode");
      setUser({ id: 12345, first_name: "Dev", username: "devuser" });
      return;
    }

    webApp.ready();
    webApp.expand();

    // Запрещаем закрытие по свайпу вниз
    if (webApp.enableClosingConfirmation) {
      webApp.enableClosingConfirmation();
    }

    setTg(webApp);
    setColorScheme(webApp.colorScheme || "dark");
    setInitData(webApp.initData || "");

    if (webApp.initDataUnsafe?.user) {
      setUser(webApp.initDataUnsafe.user);
    }

    webApp.onEvent("themeChanged", () => {
      setColorScheme(webApp.colorScheme || "dark");
    });

    setIsReady(true);
  }, []);

  const showAlert = (message) => {
    if (tg) {
      tg.showAlert(message);
    } else {
      alert(message);
    }
  };

  const showConfirm = (message) => {
    return new Promise((resolve) => {
      if (tg) {
        tg.showConfirm(message, resolve);
      } else {
        resolve(window.confirm(message));
      }
    });
  };

  const hapticFeedback = (type = "impact", style = "medium") => {
    if (tg?.HapticFeedback) {
      if (type === "impact") tg.HapticFeedback.impactOccurred(style);
      if (type === "notification") tg.HapticFeedback.notificationOccurred(style);
      if (type === "selection") tg.HapticFeedback.selectionChanged();
    }
  };

  const setBackButton = (visible, onClick) => {
    if (!tg) return;
    if (visible) {
      tg.BackButton.show();
      tg.BackButton.onClick(onClick);
    } else {
      tg.BackButton.hide();
    }
  };

  const setMainButton = (text, onClick, options = {}) => {
    if (!tg) return;
    tg.MainButton.setText(text);
    tg.MainButton.onClick(onClick);
    if (options.color) tg.MainButton.color = options.color;
    if (options.textColor) tg.MainButton.textColor = options.textColor;
    tg.MainButton.show();
  };

  const hideMainButton = () => {
    if (tg) tg.MainButton.hide();
  };

  return {
    tg,
    user,
    initData,
    colorScheme,
    isReady,
    showAlert,
    showConfirm,
    hapticFeedback,
    setBackButton,
    setMainButton,
    hideMainButton,
  };
}
