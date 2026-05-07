export interface ClientData {
  code: string;
  name: string;
  aliases: string[];
  active: boolean;
}

export interface ProjectData {
  id: string;
  code: string;
  name: string;
  default_folder_category: string;
}

export interface ProposalData {
  proposal_id: string;
  proposed_name: string;
  original_name: string;
  file_size: number;
  doc_type: string;
  client_code: string;
  project_code: string;
  folder_category: string;
  version: string;
  seq_preview: number;
}

export interface MatchResult {
  client_code: string | null;
  client_name: string | null;
  project_code: string | null;
  project_name: string | null;
  default_folder_category: string;
  confidence: number;
}
