import React from 'react';
import ReactCountryFlag from 'react-country-flag';
import countries from 'i18n-iso-countries';
import frLocale from 'i18n-iso-countries/langs/fr.json';

countries.registerLocale(frLocale);

function getAlpha2FromName(name) {
  if (!name) return null;
  const names = countries.getNames('fr');
  const entry = Object.entries(names).find(([, n]) => n && n.toLowerCase() === name.toLowerCase());
  return entry ? entry[0] : null;
}

export default function CountryBadge({ countryName, size = '48px', showLabel = true }) {
  const alpha2 = getAlpha2FromName(countryName);
  const containerStyle = { width: size, display: 'flex', flexDirection: 'column', alignItems: 'center' };
  const nameStyle = { marginTop: '0.45rem', textAlign: 'center', lineHeight: 1 };
  const flagStyle = { width: size, height: size };

  return (
    <div style={containerStyle}>
      {alpha2 ? (
        <ReactCountryFlag
          countryCode={alpha2}
          svg
          style={flagStyle}
          title={countryName}
          aria-label={countryName}
        />
      ) : (
        <div
          className="rounded-full bg-gray-100 text-gray-800 flex items-center justify-center font-semibold"
          style={{ ...flagStyle, display: 'flex' }}
        >
          {countryName ? countryName.slice(0, 2).toUpperCase() : 'NA'}
        </div>
      )}
      {showLabel && <div style={nameStyle} className="text-sm font-medium text-gray-900">{countryName}</div>}
    </div>
  );
}
