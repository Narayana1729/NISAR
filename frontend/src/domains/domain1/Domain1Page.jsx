import React from 'react';
import DomainWorkspace from '../../components/DomainWorkspace';
import { getDomainById } from '../../config/domains';

const domainConfig = getDomainById('domain1');

export default function Domain1Page() {
  return <DomainWorkspace domain={domainConfig} />;
}
