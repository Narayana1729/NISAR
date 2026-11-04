import React from 'react';
import DomainWorkspace from '../../components/DomainWorkspace';
import { getDomainById } from '../../config/domains';

const domainConfig = getDomainById('domain4');

export default function Domain4Page() {
  return <DomainWorkspace domain={domainConfig} />;
}
