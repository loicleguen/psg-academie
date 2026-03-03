import { useState } from 'react';

export default function PasswordInput({ id = 'password', value, onChange, placeholder = 'Password', className = '' }) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={`relative ${className}`}>
      <input
        id={id}
        name={id}
        type={visible ? 'text' : 'password'}
        value={value}
        onChange={onChange}
        placeholder={placeholder}
        className="rounded-none relative block w-full px-3 py-2 border border-gray-300 bg-white opacity-70 placeholder-red-700 text-gray-900 rounded-t-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z 1 sm:text-sm"
        aria-describedby={`${id}-toggle`}
      />
      <button
        type="button"
        id={`${id}-toggle`}
        aria-label={visible ? 'Masquer le mot de passe' : 'Afficher le mot de passe'}
        onClick={() => setVisible(v => !v)}
        className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-700 focus:outline-none"
        >
        <img
            src={visible ? '/images/open_eyes.png' : '/images/closed_eyes.png'}
            alt={visible ? 'oeil ouvert' : 'oeil fermé'}
            className="h-5 w-5"
            width="20"
            height="20"
            aria-hidden="true"
        />
      </button>
    </div>
  );
}